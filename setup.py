from setuptools import setup

setup(
    use_scm_version=True,
)
# In setup.py
extras_require={
    'databricks': ['pyspark>=3.0.0'],
    'dev': ['pytest', 'black', ...],
}
