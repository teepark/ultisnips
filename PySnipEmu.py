#!/usr/bin/env python
# encoding: utf-8

import vim
import string
import re

def debug(s):
    f = open("/tmp/file.txt","a")
    f.write(s+'\n')
    f.close()

def _replace_text_in_buffer( start, end, text ):
    text = self._tabstop.current_text.splitlines()

    first_line_idx = self._parent.start.line + self.start.line
    first_line = vim.current.buffer[first_line_idx][:self.start.col]

    last_line_idx = self._parent.start.line + self.end.line
    last_line = vim.current.buffer[last_line_idx][self.end.col:]
    # last_line = text[-1] + last_line

    debug("Trying to write:")

    if not len(text):
        arr = [ first_line + last_line ]
    elif len(text) == 1:
        arr = [ first_line + text[0] + last_line ]
    else:
        arr = [ first_line ] + text + [ last_line ]

    debug("%s" % (arr,))
    vim.current.buffer[first_line_idx:last_line_idx+1] = arr

    oldcolspan = self.end.col-self.start.col
    lcol = len(text[-1]) if len(text) else 0
    self._end.col = self.start.col + lcol
    newcolspan = self.end.col-self.start.col

    oldlinespan = self.end.line - self.start.line
    ll = len(text)-1 if len(text) else 0
    self._end.line = self.start.line + ll
    newlinespan = self.end.line - self.start.line



class Position(object):
    def __init__(self, line, col):
        self.line = line
        self.col = col

    def col():
        def fget(self):
            return self._col
        def fset(self, value):
            if value < 0:
                raise RuntimeError, "Invalid Column: %i" % col
            self._col = value
        return locals()
    col = property(**col())

    def line():
        doc = "Zero base line numbers"
        def fget(self):
            return self._line
        def fset(self, value):
            if value < 0:
                raise RuntimeError, "Invalid Line: %i" % line
            self._line = value
        return locals()
    line = property(**line())

class TextObject(object):
    """
    This base class represents any object in the text
    that has a span in any ways
    """
    def __init__(self, start, end):
        self._parent = None
        self._start = start
        self._end = end

    def parent():
        doc = "The parent TextObject this TextObject resides in"
        def fget(self):
            return self._parent
        def fset(self, value):
            self._parent = value
        return locals()
    parent = property(**parent())

    @property
    def start(self):
        return self._start

    @property
    def end(self):
        return self._end


class Mirror(TextObject):
    """
    A Mirror object mirrors a TabStop that is, text is repeated here
    """
    def __init__(self, ts, idx, start_col):
        start = Position(idx,start_col)
        end = Position(idx,start_col)
        TextObject.__init__(self, start, end)

        self._tabstop = ts

    @property
    def tabstop(self):
        return self._tabstop

    def update(self,ts):
        if ts != self._tabstop:
            return 0

        # _replace_text_in_buffer( self._parent.start + self._start,
        #         self._parent.start + self._end,
        #         self._tabstop.current_text
        # )
        text = self._tabstop.current_text.splitlines()

        first_line_idx = self._parent.start.line + self.start.line
        first_line = vim.current.buffer[first_line_idx][:self.start.col]

        last_line_idx = self._parent.start.line + self.end.line
        last_line = vim.current.buffer[last_line_idx][self.end.col:]
        # last_line = text[-1] + last_line

        debug("Trying to write:")

        if not len(text):
            arr = [ first_line + last_line ]
        elif len(text) == 1:
            arr = [ first_line + text[0] + last_line ]
        else:
            arr = [ first_line ] + text + [ last_line ]

        debug("%s" % (arr,))
        vim.current.buffer[first_line_idx:last_line_idx+1] = arr

        oldcolspan = self.end.col-self.start.col
        lcol = len(text[-1]) if len(text) else 0
        self._end.col = self.start.col + lcol
        newcolspan = self.end.col-self.start.col

        oldlinespan = self.end.line - self.start.line
        ll = len(text)-1 if len(text) else 0
        self._end.line = self.start.line + ll
        newlinespan = self.end.line - self.start.line


        return newlinespan-oldlinespan, newcolspan-oldcolspan


class TabStop(TextObject):
    """
    This is the most important TextObject. A TabStop is were the cursor
    comes to rest when the user taps through the Snippet.
    """
    def __init__(self, idx, span, default_text = ""):
        start = Position(idx,span[0])
        end = Position(idx,span[1])
        TextObject.__init__(self, start, end)

        self._ct = default_text

    def current_text():
        def fget(self):
            return self._ct
        def fset(self, value):
            self._ct = value
        return locals()
    current_text = property(**current_text())

    def select(self):
        lineno, col = self._parent.start.line, self._parent.start.col

        newline = lineno + self._start.line
        newcol = self._start.col

        if newline == lineno:
            newcol += col

        vim.current.window.cursor = newline + 1, newcol

        # Select the word
        # Depending on the current mode and position, we
        # might need to move escape out of the mode and this
        # will move our cursor one left
        if len(self._ct) > 0:
            if newcol != 0 and vim.eval("mode()") == 'i':
                move_one_right = "l"
            else:
                move_one_right = ""

            vim.command(r'call feedkeys("\<Esc>%sv%il\<c-g>")'
                % (move_one_right, len(self._ct)-1))


class SnippetInstance(TextObject):
    """
    A Snippet instance is an instance of a Snippet Definition. That is,
    when the user expands a snippet, a SnippetInstance is created to
    keep track of the corresponding TextObjects. The Snippet itself is
    also a TextObject because it has a start an end
    """

    def __init__(self, start, end, ts, mirrors):
        TextObject.__init__(self, start, end)

        self._tabstops = ts
        self._mirrors = mirrors
        self._text_objects = ts.values() + mirrors
        self._selected_tab = None

        self._cts = None

        for to in self._text_objects:
            to.parent = self

        for ts in self._tabstops.values():
            self._update_mirrors(ts)


    def select_next_tab(self, backwards = False):
        if self._cts == 0:
            if not backwards:
                return False

        if backwards:
            cts_bf = self._cts

            if self._cts == 0:
                self._cts = max(self._tabstops.keys())
            else:
                self._cts -= 1
            if self._cts <= 0:
                self._cts = cts_bf
        else:
            # All tabs handled?
            if self._cts is None:
                self._cts = 1
            else:
                self._cts += 1

            if self._cts not in self._tabstops:
                self._cts = 0
                if 0 not in self._tabstops:
                    return False

        ts = self._tabstops[self._cts]

        ts.select()

        self._selected_tab = ts
        return True


    def _update_mirrors(self,for_ts):
        for m in self._mirrors:
            moved_lines, moved_cols = m.update(for_ts)
            self._move_textobjects_behind(moved_lines, moved_cols, m)


    def _move_textobjects_behind(self, lines, cols, obj):
        if lines == 0 and cols == 0:
            return

        for m in self._text_objects:
            if m.start.line != obj.start.line:
                continue
            if m.start.col >= obj.start.col and m != obj:
                m.start.col += cols
                m.end.col += cols

    def backspace(self,count):
        cts = self._tabstops[self._cts]
        ll = len(cts.current_text)

        deleted_text = cts.current_text[-count:].splitlines()

        cts.current_text = cts.current_text[:-count]
        if len(deleted_text):
            self._move_textobjects_behind(-(len(deleted_text)-1),
                len(deleted_text[-1]), cts)

        self._update_mirrors(cts)

    def chars_entered(self, chars):
        cts = self._tabstops[self._cts]

        if self._selected_tab is not None:
            self._move_textobjects_behind(0, len(chars)-len(cts.current_text), cts)
            cts.current_text = ""
            self._selected_tab = None
        else:
            text = chars.splitlines()
            if len(text):
                self._move_textobjects_behind(len(text)-1, len(text[-1]), cts)

        cts.current_text += chars

        self._update_mirrors(cts)


class Snippet(object):
    _TABSTOP = re.compile(r'''(?xms)
(?:\${(\d+):(.*?)})|   # A simple tabstop with default value
(?:\$(\d+))           # A mirror or a tabstop without default value.
''')

    def __init__(self,trigger,value):
        self._t = trigger
        self._v = value

    @property
    def trigger(self):
        return self._t

    def _handle_tabstop(self, m, val, tabstops, mirrors):
        no = int(m.group(1))
        def_text = m.group(2)

        start, end = m.span()
        val = val[:start] + def_text + val[end:]

        line_idx = val[:start].count('\n')
        line_start = val[:start].rfind('\n') + 1
        start_in_line = start - line_start
        ts = TabStop(line_idx,
                (start_in_line,start_in_line+len(def_text)), def_text)

        tabstops[no] = ts

        return val

    def _handle_ts_or_mirror(self, m, val, tabstops, mirrors):
        no = int(m.group(3))

        start, end = m.span()
        val = val[:start] + val[end:]

        line_idx = val[:start].count('\n')
        line_start = val[:start].rfind('\n') + 1
        start_in_line = start - line_start

        if no in tabstops:
            m = Mirror(tabstops[no], line_idx, start_in_line)
            mirrors.append(m)
        else:
            ts = TabStop(line_idx, (start_in_line,start_in_line))
            tabstops[no] = ts

        return val

    def _find_tabstops(self, val):
        tabstops = {}
        mirrors = []

        while 1:
            m = self._TABSTOP.search(val)

            if m is not None:
                if m.group(1) is not None: # ${1:hallo}
                    val = self._handle_tabstop(m,val,tabstops,mirrors)
                elif m.group(3) is not None: # $1
                    val = self._handle_ts_or_mirror(m,val,tabstops,mirrors)
            else:
                break

        return tabstops, mirrors, val.split('\n')

    def launch(self, before, after):
        lineno,col = vim.current.window.cursor

        col -= len(self._t)

        ts, mirrors, lines = self._find_tabstops(self._v)

        endcol = None
        newline = 1
        newcol = 0
        if not len(ts):
            newline = lineno + len(lines) - 1
            if len(lines) == 1:
                newcol = col + len(lines[-1])
            else:
                newcol = len(lines[-1])

        lines[0] = before + lines[0]
        lines[-1] += after

        vim.current.buffer[lineno-1:lineno-1+1] = lines

        vim.current.window.cursor = newline, newcol

        if len(ts) or len(mirrors):
            s = SnippetInstance(
                Position(lineno-1,col), Position(newline-1,newcol),
                ts, mirrors)

            s.select_next_tab()

            return s

class SnippetManager(object):
    def __init__(self):
        self.reset()
        self._last_cursor_pos = None

    def reset(self):
        self._snippets = {}
        self._current_snippets = []

    def add_snippet(self,trigger,value):
        self._snippets[trigger] = Snippet(trigger,value)

    def try_expand(self, backwards = False):
        if len(self._current_snippets):
            cs = self._current_snippets[-1]
            if not cs.select_next_tab(backwards):
                self._current_snippets.pop()
            self._last_cursor_pos = vim.current.window.cursor
            return

        line = vim.current.line

        dummy,col = vim.current.window.cursor

        if col > 0 and line[col-1] in string.whitespace:
            return

        # Get the word to the left of the current edit position
        before,after = line[:col], line[col:]

        word = before.split()[-1]
        if word in self._snippets:
            s = self._snippets[word].launch(before.rstrip()[:-len(word)], after)
            self._last_cursor_pos = vim.current.window.cursor
            if s is not None:
                self._current_snippets.append(s)

    def cursor_moved(self):
        cp = vim.current.window.cursor

        if len(self._current_snippets) and self._last_cursor_pos is not None:
            lineno,col = cp
            llineo,lcol = self._last_cursor_pos
            if lineno in \
                [ self._last_cursor_pos[0], self._last_cursor_pos[0]+1]:
                cs = self._current_snippets[-1]

                # Detect a carriage return
                if col == 0 and lineno == self._last_cursor_pos[0] + 1:
                    cs.chars_entered('\n')
                elif lcol > col: # Some deleting was going on
                    cs.backspace(lcol-col)
                else:
                    line = vim.current.line

                    chars = line[lcol:col]
                    cs.chars_entered(chars)

        self._last_cursor_pos = cp

    def entered_insert_mode(self):
        pass

PySnipSnippets = SnippetManager()

