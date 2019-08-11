import datetime
import sys

from hildebrand import Glow

def main(args=None):
    glow = Glow()
    print("Access Token: {}\n".format(glow.accessToken))
    print("Account ID {}\n".format(glow.accountId))
    print("Expires: {}\n".format(glow.expiration))

if __name__ == '__main__':
    main()
