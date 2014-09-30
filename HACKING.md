How to hack on timestreamlib
=======================

Git Usage
------------

Merge is evil, for day-to-day usage it make the git history graph look like a
bowl of spaghetti. Use `git rebase`.

Please `git fetch --all` before every commit, and `git push` after every
commit. It helps with the above (and below).

###Commits

**BEFORE COMMITING**: run `./run_tests`. If the tests don't pass, don't commit.
Or, if you must, put "!BROKEN!" or similar in the header and create an issue on
github explaining what broke & what needs fixing.

Commit style:
- Lines no longer than 72 chars
- First line **strictly** less than 51 chars
- First line a brief comment of the commit (one line)
- The second line is always blank
- A list of changed files (I do this automatically with vc-dwim)
- If large general description is needed put it after the second blank line and
  before the file list.
- Try to explain what was done :). "Fixed bug" does not count :)
- Use github issue numbers if you're addressing an issue, and github
  auto-references the commit from the issue

For very simple commits, use this shorthand:
```
[<filename>] Message
```

For example:

```
[run_tests] Use git submodule to update test/data
```

Any commit that touches more than one file, or needs more explanation should
follow the following guide:

```
First line description

A more general Description. Can be longer
* path/to/file/that/changed1 (method): This is what the change did
* path/to/file/that/changed2: This is a general change
```


###Branches

`master` is for stable code. It must run without error, have no known bugs,
have documentation & tests, and follow all code style guidelines we care about.
Major feature branches should have no known bugs, but may or may not be well
tested/documented and may be full of weird or hacky code (e.g. the
`traitcapture_v0` branch). Bugs in a major feature branch' HEAD should be fixed
as a matter of priority. Active development should happen in individual,
per-person forks of the relevant major feature branch. Use minor feature
branches if helps when you're working on several distinct features, but use
`git rebase` to get them into the main major feature branch (preferably in
coherent chunks, all addressing a single feature, not interleaved between many
minor features).

Coding Style
------

All python code should follow
[pep8](http://legacy.python.org/dev/peps/pep-0008/), and should not have any
errors as judged by [flake8](https://flake8.readthedocs.org/en/2.1.0/), a tool
which checks PEP8 compliance, and a few other styles & conventions.
[autopep8](https://pypi.python.org/pypi/autopep8/) can automatically fix some
more common & simple PEP8 errors.

Documentation
-------------------

Simple API docs should be written into docstrings in a way that
[Sphinx](http://sphinx-doc.org/) can parse using the
[autodoc extension](http://sphinx-doc.org/ext/autodoc.html). A guide on doing
so is [here](https://pythonhosted.org/an_example_pypi_project/sphinx.html).
Longer, more verbose docs should be written in RST, under ./docs, as has been
started in the docs branch.

Testing
----------

I don't like doctests, they cause weird formatting issues & can randomly break
for no reason.

Every public function/class/method should have unit tests, implemented as
subclasses of `unittest.TestCase`. All probable inputs, including erroneous
ones, should be tested. "friendly" and "nasty" test cases should be separate
functions. I.e., have one test case that checks for sane output on good input,
and a separate test case that gives invalid input, especially things like
broken input files. These tests should also be useful as documentation of how
to and how not to use the API, so keep them readable and sane.

Unit tests often require long-winded literal values. In this case, store all
literals in an external file, e.g a JSON file, and read literals into the test
case classes using the `setUp(self)` function. This ensures that testing code
is readable, and not polluted with endless `dict`s of expected output.

Tests can and should be run using `./run_tests`.
