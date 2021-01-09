# ICEIndexScrapper

Download index data from https://indices.theice.com/home

## Install
```sh
git clone https://github.com/zoticusbarns/ICEIndexScrapper.git
python -m pip install -r requirements.txt
```

Open main.py using any text editor and modify the few line of code
```python
date = "09/30/2020"  # valuation date in the format of mm/dd/yyyy
path = ""  # Path to Chrome web driver
user_id = ""  # login user name
```

Run the script using python in terminal

```sh
python main.py
```