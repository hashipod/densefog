## publish to pypi

pip install build twine


```
python3 -m build --sdist ./
python3 -m build --wheel ./

# check dist folder

twine upload dist/xxxx.tar.gz dist/yyyyy.whl

```
