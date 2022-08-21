import collections
import string


try:
    from StringIO import StringIO
except ImportError:
    from io import (StringIO, BytesIO)


class Lexer(object):
    """
    Simple Lexer base class. Provides basic lexer framework and
    helper functionality (read/peek/pushback/etc)

    Grammar is implemented via 'lexXXXX' methods which match tokens
    in the input stream and return a (token,lexYYYY) tuple with
    lexYYYY being a method encapsulating the next state (None to stop).

    See WordLexer below for example.

    The 'parse' method returns a generator that will return tokens
    (the class also acts as an iterator)

    The default start state is 'lexStart'. This approach is based loosely on
    Rob Pike's Go lexer presentation (uses generators rather than channels).
    """

    escape_chars = '\\'
    escape = {'n': '\n', 't': '\t', 'r': '\r'}

    def __init__(self, f, debug=False):
        if hasattr(f, 'read'):
            self.f = f
        elif type(f) == str:
            self.f = StringIO(f)
        elif type(f) == bytes:
            self.f = BytesIO(f.decode())
        else:
            raise ValueError("Invalid input")
        self.debug = debug
        self.q = collections.deque()
        self.state = self.lexStart
        self.escaped = False
        self.eof = False

    def __iter__(self):
        return self.parse()

    def next_token(self):
        if self.debug:
            print("STATE", self.state)
        (tok, self.state) = self.state()
        return tok

    def parse(self):
        while self.state is not None and not self.eof:
            tok = self.next_token()
            if tok:
                yield tok

    def read(self, n=1):
        s = ""
        while self.q and n > 0:
            s += self.q.popleft()
            n -= 1
        s += self.f.read(n)
        if s == '':
            self.eof = True
        if self.debug:
            print("Read: >%s<" % repr(s))
        return s

    def peek(self, n=1):
        s = ""
        i = 0
        while len(self.q) > i and n > 0:
            s += self.q[i]
            i += 1
            n -= 1
        r = self.f.read(n)
        if n > 0 and r == '':
            self.eof = True
        self.q.extend(r)
        if self.debug:
            print("Peek : >%s<" % repr(s + r))
        return s + r

    def pushback(self, s):
        p = collections.deque(s)
        p.extend(self.q)
        self.q = p

    def readescaped(self):
        c = self.read(1)
        if c in self.escape_chars:
            self.escaped = True
            n = self.peek(3)
            if n.isdigit():
                n = self.read(3)
                if self.debug:
                    print("Escape: >%s<" % n)
                return chr(int(n, 8))
            elif n[0] in 'x':
                x = self.read(3)
                if self.debug:
                    print("Escape: >%s<" % x)
                return chr(int(x[1:], 16))
            else:
                c = self.read(1)
                if self.debug:
                    print("Escape: >%s<" % c)
                return self.escape.get(c, c)
        else:
            self.escaped = False
            return c

    def lexStart(self):
        return (None, None)


class WordLexer(Lexer):
    """
    Example lexer which will split input stream into words (respecting quotes)
    """
    wordchars = set(string.ascii_letters) | set(string.digits) | set(string.punctuation)
    quotechars = set('"\'')
    commentchars = set('#')
    spacechars = set(' \t\r\x0b\x0c')
    nlchars = set('\n')
    spacetok = None
    nltok = None

    def lexStart(self):
        return None, self.lexSpace

    def lexSpace(self):
        s = []
        while not self.eof:
            c = self.peek()
            if c in self.spacechars:
                s.append(self.read())
            elif c in self.nlchars:
                return self.spacetok, self.lexNL
            elif c in self.commentchars:
                return self.spacetok, self.lexComment
            elif c in self.quotechars:
                return self.spacetok, self.lexQuote
            elif c in self.wordchars:
                return self.spacetok, self.lexWord
            elif c:
                raise ValueError("Invalid input [%d]: %s" % (
                    self.f.tell(), c))
        return None, None

    def lexNL(self):
        self.read()
        return self.nltok, self.lexSpace

    def lexComment(self):
        s = []
        tok = lambda n: (('COMMENT', ''.join(s)), n) if s else (None, n)
        start = False
        _ = self.read()
        while not self.eof:
            c = self.read()
            if c == '\n':
                self.pushback(c)
                return tok(self.lexNL)
            elif start or c not in string.whitespace:
                start = True
                s.append(c)
        return tok(None)

    def lexWord(self):
        s = []
        tok = lambda n: (('ATOM', ''.join(s)), n) if s else (None, n)
        while not self.eof:
            c = self.peek()
            if c == '"':
                return tok(self.lexQuote)
            elif c in self.commentchars:
                return tok(self.lexComment)
            elif c.isspace():
                return tok(self.lexSpace)
            elif c in self.wordchars:
                s.append(self.read())
            elif c:
                raise ValueError('Invalid input [%d]: %s' % (
                    self.f.tell(), c))
        return tok(None)

    def lexQuote(self):
        s = []
        tok = lambda n: (('ATOM', ''.join(s)), n) if s else (None, n)
        q = self.read(1)
        while not self.eof:
            c = self.readescaped()
            if c == q and not self.escaped:
                break
            else:
                s.append(c)
        return tok(self.lexSpace)


if __name__ == '__main__':
    l = WordLexer(r'abc "def\100\x3d\. ghi" jkl')
    print(list(l))
    # -> [('ATOM', 'abc'), ('ATOM', 'def@=. ghi'), ('ATOM', 'jkl')]

    l = WordLexer(r"1 '2 3 4' 5")
    print(list(l))
    # -> [('ATOM', '1'), ('ATOM', '2 3 4'), ('ATOM', '5')]

    l = WordLexer("abc# a comment")
    print(list(l))
    # -> [('ATOM', 'abc'), ('COMMENT', 'a comment')]
