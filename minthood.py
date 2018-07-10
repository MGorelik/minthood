from getpass import getpass

import keyring

from mint.api import MintApi
from robinhood.api import RobinhoodApi


def main():
    username = input("Robinhood username: ")
    password = keyring.get_password("minthood-robinhood", username)

    if not password:
        password = getpass("Robinhood password: ")

    robinhood = RobinhoodApi(username, password)

    login = robinhood.login()

    if login:
        # store valid creds
        keyring.set_password("minthood-robinhood", username, password)

        # get accounts
        robinhood_accounts = robinhood.get_accounts()

        # try getting portfolio $
        portfolio_values = {}
        for account in robinhood_accounts:
            portfolio = robinhood.get_portfolio(account)
            equity = portfolio.get('equity') if portfolio.get('equity') else 0
            equity_after_hours = portfolio.get('extended_hours_equity') if portfolio.get('extended_hours_equity') else 0
            portfolio_value = max(float(equity), float(equity_after_hours))
            portfolio_values[account.get('account_number')] = portfolio_value

        # update the corresponding account in Mint
        username = input("Mint username: ")

        password = keyring.get_password("minthood-mint", username)

        if not password:
            password = getpass("Mint password: ")

        try:
            mint = MintApi(username, password)
        except Exception as e:
            raise e

        # store valid creds
        keyring.set_password("minthood-mint", username, password)

        mint_accounts = mint.get_accounts()

        ROBINHOOD_PREFIX = 'Robinhood-'
        mint_rb_accounts = [mn for mn in mint_accounts if ROBINHOOD_PREFIX in mn.get('name')]

        # if we don't already have a mint account for a robinhood one, create it
        if len(robinhood_accounts) > len(mint_rb_accounts):
            for rb_account in robinhood_accounts:
                rb_name = rb_account.get('account_number')
                exists = False
                for mn_account in mint_rb_accounts:
                    mn_name = mn_account.get('name')

                    if rb_name == mn_name:
                        exists = True
                if not exists:
                    try:
                        created = mint.create_property_account(f"{ROBINHOOD_PREFIX}{rb_name}", portfolio_values[rb_name])
                        if created.get('success'):
                            print(f"Created Mint account for Robinhood account {rb_name}")
                        else:
                            print(f"Problem creating Mint account for Robinhood account {rb_name}: {created.get('error')}")
                    except Exception as e:
                        raise e

        for account in mint_accounts:
            account_name = account.get('name')

            idx = account_name.find(ROBINHOOD_PREFIX)
            account_num = account_name[idx+len(ROBINHOOD_PREFIX):] if idx > -1 else ''

            if ROBINHOOD_PREFIX in account_name and account_num:
                updated = mint.set_property_account_value(account, portfolio_values.get(account_num))

                if updated.get('success'):
                    print(f"Updated value for account {account_name}")
                else:
                    print(f"Problem updating account {account_name}: {updated.get('error')}")


main()
