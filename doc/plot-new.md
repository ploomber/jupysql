---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.14.4
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

```{code-cell} ipython3
%load_ext sql
```

```{code-cell} ipython3
import pandas as pd
import numpy as np
from sqlalchemy import create_engine

engine = create_engine("duckdb:///:memory:")
engine.execute("register", ("df", pd.DataFrame({"x": np.random.rand(1000)})))
```

```{code-cell} ipython3
%sql engine
```

```{code-cell} ipython3
%sql
```

```{code-cell} ipython3
%sqlplot box -t df -c x
```

```{code-cell} ipython3
%sqlplot hist -t df -c x -b 100
```

```{code-cell} ipython3

```
