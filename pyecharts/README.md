## Pain YCSB Graph with Pyecharts

### Usage

```
pip install -r requirements.txt
python graph.py <root-path>
```

Then the painter will walk through all of the files end with `.result` under the root directory `<root-path>`

### Filename Constraint

The file name format should be `{DB}-{oprCount}-{threadCount}-{workload}.result`

