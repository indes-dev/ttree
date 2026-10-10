# TASK-003 amendment 3: isolated startup candidate

N-1 is corrected first. The worker uses the selected interpreter with `-I`,
from its private temporary directory, with the existing allowlisted environment
and inherited descriptor boundary. Python isolated mode excludes caller cwd,
user site and PYTHON environment configuration (including Python 3.10).
Reference: https://docs.python.org/3.10/using/cmdline.html#cmdoption-I.

The fixed provisional wheel passed a harmless installed-console regression on
CPython 3.12.14: caller `ttree` package, tiktoken/pypdf/ctypes/json and sitecustomize
markers did not run; text/DOCX/PDF retained counts 4/4/3. Wheel bounded module bytes
match fixed source. Evidence: review/task-003/evidence/amendment-3-startup/.
This provisional wheel is not the final tracked artifact. Four installed runtimes,
remaining base corrections and one native observation continue under amendment 3.
No pre-fix exploit was executed. No independent finding is self-closed. Overall
TASK-003 remains 0/4; native phase 1 and changed-SHA independent acceptance are open.
