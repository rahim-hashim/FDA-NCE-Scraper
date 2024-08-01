import sys
from getpass import getpass

def rs_login():
  import robin_stocks.robinhood as rs
  p = getpass(prompt='Robinhood Password: ')
  rs.login(username="rahimh233@gmail.com",
           password=p,
           expiresIn=84600,
           by_sms=True)

# Login
def login_helper(installs_path=None):
  # freeze pip install for Google Colab use
  try:
    rs_login()
    print('robin_stocks imported')
    return True
  except:
    print('robin_stocks not installed')
    return False
