from bitshares.storage import DataDir as BTSDataDir
from appdirs import user_data_dir, system
import json

import os
import logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.StreamHandler())

timeformat = "%Y%m%d-%H%M%S"

class DataDir(BTSDataDir):
    """ This class ensures that the user's data is stored in its OS
        preotected user directory:

        **OSX:**

         * `~/Library/Application Support/<AppName>`

        **Windows:**

         * `C:\\Documents and Settings\\<User>\\Application Data\\Local Settings\\<AppAuthor>\\<AppName>`
         * `C:\\Documents and Settings\\<User>\\Application Data\\<AppAuthor>\\<AppName>`

        **Linux:**

         * `~/.local/share/<AppName>`

         Furthermore, it offers an interface to generated backups
         in the `backups/` directory every now and then.
    """
    appname = "bitshares"
    appauthor = "Fabian Shuch"
    storageDatabaseDefault = "bitshares.sqlite"

    @classmethod
    def preflight(self, filename=True):
        d = user_data_dir(self.appname, self.appauthor)
        if "linux" in system:
            d = os.path.expanduser("~/.bitshares/")
        if not(os.path.isdir(d)): # Hack - create directory in advance
            os.makedirs(d, exist_ok=True)
        if not filename:
            return d
        return os.path.join(d, self.storageDatabaseDefault)

class Accounts(DataDir):
    """ This is the account storage that stores account names,
        ids, full blockchain dump and a dict of balances
        in the `accounts` table in the SQLite3 database.
    """
    __tablename__ = 'accounts'
    __columns__ = [ 'id', 'account', 'account_id', 'graphene_json', 'balances_json' ]

    def __init__(self, *args, **kwargs):
        super(Accounts, self).__init__(*args, **kwargs)

    def create_table(self):
        """ Create the new table in the SQLite database
        """
        query = ('CREATE TABLE %s (' % self.__tablename__ +
                 'id INTEGER PRIMARY KEY AUTOINCREMENT,' +
                 'account STRING(256),' +
                 'account_id STRING(256),' +
                 'graphene_json TEXT,' +
                 'balances_json TEXT,' +
                 'keys INTEGER'
                 ')',)
        self.sql_execute(query)

    def getAccounts(self):
        """ Returns all accounts stored in the database
        """
        query = ("SELECT account from %s " % (self.__tablename__), )
        results = self.sql_fetchall(query)
        return [x[0] for x in results]

    def getBy(self, key, some_id):
        """
        """
        if key not in ['account', 'account_id']:
            raise KeyError("'key' must be account or account_id")
        query = ("SELECT graphene_json, balances_json, account, account_id from %s " % (self.__tablename__) +
                 "WHERE %s=?" % (key),
                 (some_id, ))
        row = self.sql_fetchone(query)
        if not row:
            return None

        body = json.loads(row[0])
        body['balances'] = json.loads(row[1]) if row[1] else { }
        body['name'] = row[2]
        body['id'] = row[3]
        return body

    def getById(self, account_id):
        return self.getBy('account_id', account_id)

    def getByName(self, account_name):
        return self.getBy('account', account_name)

    def update(self, account_name, key, val):
        """
        """
        if not(key in ['graphene_json','balances_json']):
            raise ValueError("'key' must be graphene_json or balances_json")
        if key == 'graphene_json':
           val.pop('balances', None)
        query = ("UPDATE %s " % self.__tablename__ +
                 ("SET %s=? WHERE account=?" % key),
                 (json.dumps(val), account_name))
        self.sql_execute(query)

    def add(self, account_name, account_id=None, keys=2):
        """ Add an account

           :param str account_name: Account name
        """
        if self.getByName(account_name):
            raise ValueError("Account already in storage")
        query = ('INSERT INTO %s (account, account_id, keys) ' % self.__tablename__ +
                 'VALUES (?, ?, ?)',
                 (account_name, account_id, keys, ))
        self.sql_execute(query)

    def delete(self, account_name):
        """ Delete the record identified as `account_name`

           :param str account_name: Account name
        """
        query = ("DELETE FROM %s " % (self.__tablename__) +
                 "WHERE account=?",
                 (account_name))
        self.sql_execute(query)

    def wipe(self):
        """ Delete ALL entries
        """
        query = ("DELETE FROM %s " % (self.__tablename__),)
        self.sql_execute(query)



class Label(DataDir):
    """ This is the account storage that stores account names,
        and optional public keys (for cache sake)
        in the `accounts` table in the SQLite3 database.
    """
    __tablename__ = 'labels'

    def __init__(self, *args, **kwargs):
        super(Label, self).__init__(*args, **kwargs)

    def create_table(self):
        """ Create the new table in the SQLite database
        """
        query = ('CREATE TABLE %s (' % self.__tablename__ +
                 'id INTEGER PRIMARY KEY AUTOINCREMENT,' +
                 'label STRING(256),' +
                 'pub STRING(256)' +
                 ')', )
        self.sql_execute(query)

    def getLabels(self):
        """ Returns all labels stored in the database
        """
        query = ("SELECT label from %s " % (self.__tablename__))
        result = self.sql_fetchall(query)
        return [x[0] for x in results]

    def updateKey(self, label, pub):
        """ Change the wif to a pubkey

           :param str pub: Public key
           :param str wif: Private key
        """
        query = ("UPDATE %s " % self.__tablename__ +
                 "SET pub=? WHERE label=?",
                 (pub, label))
        self.sql_execute(query)

    def add(self, label, pub):
        """ Add an account

           :param str account_name: Account name
        """
        if self.getLabel(label):
            raise ValueError("Label already in storage")
        query = ('INSERT INTO %s (label, pub) ' % self.__tablename__ +
                 'VALUES (?, ?)',
                 (label, pub))
        self.sql_execute(query)

    def delete(self, label):
        """ Delete the record identified as `label`

           :param str label: Label
        """
        query = ("DELETE FROM %s " % (self.__tablename__) +
                 "WHERE label=?",
                 (label))
        self.sql_execute(query)



class History(DataDir):
    """ This is the account storage that stores account names,
        and optional public keys (for cache sake)
        in the `accounts` table in the SQLite3 database.
    """
    __tablename__ = 'history'
    __columns__ = [
        "id", "account", "description", "op_index",
        "operation", "memo", "block_num", "trx_in_block",
        "op_in_trx", "virtual_op", "trxid", "trxfull", "details", "date" ]

    def __init__(self, *args, **kwargs):
        super(History, self).__init__(*args, **kwargs)

    def create_table(self):
        """ Create the new table in the SQLite database
        """
        query = ('CREATE TABLE %s (' % self.__tablename__ +
                 'id INTEGER PRIMARY KEY AUTOINCREMENT,' +
                 'account STRING(256),' +
                 'description STRING(512),' +
                 'op_index STRING(256),' +

                 'operation TEXT,' +
                 'memo INTEGER,' +
                 'block_num INTEGER,' +
                 'trx_in_block INTEGER,' +
                 'op_in_trx INTEGER,' +
                 'virtual_op INTEGER,' +
                 'trxid STRING(256),' +
                 'trxfull TEXT,' +

                 'details TEXT,' +
                 'date TEXT'
                 ')', )
        self.sql_execute(query)

    def getEntries(self, account_name):
        """ Returns all entries stored in the database
        """
        query = (("SELECT * from %s " % self.__tablename__) +
            "WHERE account=? ORDER BY CAST(substr(op_index,6) as INTEGER) DESC ",
            (account_name,)
        )
        rows = self.sql_fetchall(query)
        return self.sql_todict(self.__columns__, rows)

    def getLastOperation(self, account_name):
        query = (("SELECT op_index from %s " % self.__tablename__) +
            "WHERE account=? ORDER BY CAST(substr(op_index,6) as INTEGER) DESC LIMIT 1",
            (account_name,)
        )
        op = self.sql_fetchone(query)
        if not op:
            return None
        return op[0]

    def getEntry(self, op_index, account_name):
        query = (("SELECT * from %s " % self.__tablename__) +
            "WHERE op_index=? AND account=?",
            (op_index,account_name,)
        )
        row = self.sql_fetchone(query)
        if not row:
            return None
        return self.sql_todict(self.__columns__, [row])[0]


    def updateEntryMemo(self, id, memo):
        """ Change the memo of an entry

           :param str id: Internal database ID
           :param str memo: Memo text
        """
        query = ("UPDATE %s " % self.__tablename__ +
                 "SET memo=? WHERE id=?",
                 (memo, id))
        self.sql_execute(query)

    def updateDate(self, op_index, date):
        """ Change the date of an entry

           :param str op_index
           :param str date
        """
        query = ("UPDATE %s " % self.__tablename__ +
                 "SET date=? WHERE op_index=?",
                 (date, op_index))
        self.sql_execute(query)


    def add(self, account, description,
            op_index, operation, memo,
            block_num, trx_in_block, op_in_trx, virtual_op,
            trxid, trxfull, details):
        """ Add an entry

           :param str account_name: Account name
           :param str description: Short description
        """
        if self.getEntry(op_index, account):
            raise ValueError("Entry already in storage")

        query = ('INSERT INTO %s (' % self.__tablename__ +
                'account, description,'+
                'op_index, operation, memo,'+
                'block_num, trx_in_block, op_in_trx, virtual_op,'+
                'trxid, trxfull, details, date'+
                ') '  +
           'VALUES (?,?,  ?,?,?,  ?,?,?,?,  ?,?,?,datetime(CURRENT_TIMESTAMP) )',
           (account, description,
            op_index, operation, memo,
            block_num, trx_in_block, op_in_trx, virtual_op,
            trxid, trxfull, details))
        self.sql_execute(query)

    def delete(self, id):
        """ Delete the record identified by `id`

           :param int id: Internal db id
        """
        query = ("DELETE FROM %s " % (self.__tablename__) +
                 "WHERE id=?",
                 (id))
        self.sql_execute(query)

    def wipe(self):
        """ Delete ALL entries
        """
        query = ("DELETE FROM %s " % (self.__tablename__),)
        self.sql_execute(query)


class ExternalHistory(DataDir):
    """ This is the account storage that stores account names,
        and optional public keys (for cache sake)
        in the `accounts` table in the SQLite3 database.
    """
    __tablename__ = 'payments'
    __columns__ = [
        "id", "account", "gateway", "ioflag",
        "inputcointype", "outputcointype", "outputaddress",
        "receipt_json", "remote_json", "coindata_json", "walletdata_json",
        "creationdate" ]

    def __init__(self, *args, **kwargs):
        super(ExternalHistory, self).__init__(*args, **kwargs)

    def create_table(self):
        """ Create the new table in the SQLite database
        """
        query = ('CREATE TABLE %s (' % self.__tablename__ +
                 'id INTEGER PRIMARY KEY AUTOINCREMENT,' +
                 'account STRING(256),' +
                 'gateway STRING(256),' +
                 'ioflag INTEGER,' +
                 'inputoutput INTEGER,' +
                 'inputcointype STRING(32),' +
                 'outputcointype STRING(32),' +
                 'outputaddress STRING(256),' +
                 'receipt_json TEXT,'+
                 'remote_json TEXT,' +
                 'coindata_json TEXT,' +
                 'walletdata_json TEXT,' +
                 'creationdate TEXT'
                 ')', )
        self.sql_execute(query)


    def getAllEntries(self):
        """ Returns all entries stored in the database
        """
        query = ("SELECT " +
            (",".join(self.__columns__)) +
            (" FROM %s " % self.__tablename__)
            ,
        )
        rows = self.sql_fetchall(query)
        return self.sql_todict(self.__columns__, rows)


    def getEntries(self, account_name):
        """ Returns all entries stored in the database
        """
        query = ("SELECT " +
            (",".join(self.__columns__)) +
            (" FROM %s " % self.__tablename__) +
            "WHERE account=?",
            (account_name,)
        )
        rows = self.sql_fetchall(query)
        return self.sql_todict(self.__columns__, rows)

    def getEntry(self, id, key="gatewayid"):
        if key not in self.__columns__:
            raise KeyError("Key %s not in columns" % key)
        query = ("SELECT " +
            (",".join(self.__columns__)) + 
            (" FROM %s " % self.__tablename__) +
            ("WHERE %s=? " % key),
            (id,)
        )
        row = self.sql_fetchone(query)
        return self.sql_todict(self.__columns__, [row])[0]

    def updateEntry(self, id, key, val):
        """ Change the memo of an entry

           :param str id: Internal db id 
           :param str key: Table filed to update
           :param str val: Value to set
        """
        if key not in self.__columns__:
            raise ValueError("%s not in columns" % key)
        query = ("UPDATE %s " % self.__tablename__ +
                 "SET %s=? WHERE id=?" % key ,
                 (val, id))
        self.sql_execute(query)

    def updateCoinData(self, gatewayName, coinType, coindata_json, walletdata_json):
        """ Change the memo of an entry

           :param str id: Internal db id 
           :param str key: Table filed to update
           :param str val: Value to set
        """
        #if key not in self.__columns__:
        #   raise ValueError("%s not in columns" % key)
        query = ("UPDATE %s " % self.__tablename__ +
                 "SET coindata_json=?, walletdata_json=? WHERE gateway=? AND inputcointype=?" ,
                 (coindata_json, walletdata_json,  gatewayName, coinType))
        self.sql_execute(query)

    def add(self, account, gateway, ioflag,
                 inputcointype, outputcointype, outputaddress,
                 receipt_json, coindata_json, walletdata_json):
        """ Add an entry
        """
        #if self.getEntry(gateway, gatewayid):
        #   raise ValueError("Entry already in storage")

        query = ('INSERT INTO %s (' % self.__tablename__ +
                 'account, gateway, ioflag, ' +
                 'inputcointype, outputcointype, outputaddress,' +
                 'receipt_json, coindata_json, walletdata_json, creationdate'
                 ') '  +
           'VALUES (?,?,?,  ?,?,?,  ?,?,?, datetime(CURRENT_TIMESTAMP) )',
           (account, gateway, ioflag,
                 inputcointype, outputcointype, outputaddress,
                 receipt_json, coindata_json, walletdata_json))
        id = self.sql_execute(query, lastid=True)
        return id

    def delete(self, id):
        """ Delete the record identified by `id`

           :param int id: Internal db id
        """
        query = ("DELETE FROM %s " % (self.__tablename__) +
                 "WHERE id=?",
                 (id, ))
        self.sql_execute(query)


class Remotes(DataDir):
    """
    """
    __tablename__ = 'remotes'
    __columns__ = [ 'id', 'label', 'url', 'rtype', 'ctype' ]

    def __init__(self, *args, **kwargs):
        super(Remotes, self).__init__(*args, **kwargs)

    def create_table(self):
        """ Create the new table in the SQLite database
        """
        query = ('CREATE TABLE %s (' % self.__tablename__ +
                 'id INTEGER PRIMARY KEY AUTOINCREMENT,' +
                 'label STRING(256),' +
                 'url STRING(1024),' +
                 'rtype INTEGER,' +
                 'ctype STRING(256)' +
                 ')', )
        self.sql_execute(query)

    def getRemotes(self, rtype):
        """
        """
        query = ("SELECT id, label, url, rtype, ctype from %s WHERE rtype = ?" % (self.__tablename__), (rtype,))
        rows = self.sql_fetchall(query)
        return self.sql_todict(self.__columns__, rows)

    def add(self, rtype, label, url, ctype):
        """
        """
        query = ('INSERT INTO %s (label, url, ctype, rtype) ' % self.__tablename__ +
                 'VALUES (?, ?, ?, ?)',
                 (label, url, ctype, rtype))
        return self.sql_execute(query, lastid=True)

    def update(self, id, key, val):
        """
            :param id internal db id
            :param key key to update
            :param val value
        """
        query = ('UPDATE %s SET %s = ? ' % (self.__tablename__, key) +
                 'WHERE id = ?',
                 (val, id))
        return self.sql_execute(query)

    def delete(self, id):
        """ Delete entry by internal database id
        """
        query = ("DELETE FROM %s " % (self.__tablename__) +
                 "WHERE id=?",
                 (id,))
        self.sql_execute(query)

    def wipe(self):
        """ Delete ALL entries
        """
        query = ("DELETE FROM %s " % (self.__tablename__),)
        self.sql_execute(query)


class Assets(DataDir):
    """ This is the asset storage that stores asset names,
        ids, issuer_ids, and related graphene json data
        in the `assets` table in the SQLite3 database.
    """
    __tablename__ = 'assets'

    def __init__(self, *args, **kwargs ):
        super(Assets, self).__init__(*args, **kwargs)
        self.symbols_to_ids = { }
        self.ids_to_symbols = { }
        self.loaded_assets = { }

    def create_table(self):
        """ Create the new table in the SQLite database
        """
        query = ('CREATE TABLE %s (' % self.__tablename__ +
                 'id INTEGER PRIMARY KEY AUTOINCREMENT,' +
                 'symbol STRING(256),' +
                 'asset_id STRING(256),' +
                 'issuer_id STRING(256),' +
                 'graphene_json TEXT' +
                 ')', )
        self.sql_execute(query)

    def getAssets(self, invert_keys=None):
        """ Returns all assets cached in the database
            if `invert_keys` is None, returns a list of asset names
            if it is True, returns a dict of ids=>symbol mappings
            if it is False, returns a dict of symbol=>id mappings
        """
        query = ("SELECT asset_id, symbol, graphene_json from %s " % (self.__tablename__))
        result = self.sql_fetchall(query)
        for result in results:
            id = result[0]
            sym = result[1]
            self.symbols_to_ids[sym] = id
            self.ids_to_symbols[id] = sym

            self.loaded_assets[id] = json.loads(result[3])

        if invert_keys == False:
            return self.symbols_to_ids

        if invert_keys == True:
            return self.ids_to_symbols

        return self.loaded_assets #symbols_to_ids.keys()

    def getAssetsLike(self, name, ordered=False, limit=None):
        """
        """
        extra = ""
        if ordered:
            extra += " ORDER BY symbol"
        if limit:
            extra += " LIMIT %d" % (limit)
        query = ("SELECT graphene_json FROM %s " % (self.__tablename__) +
                 "WHERE symbol LIKE ? OR symbol LIKE ?" + extra,
                (name+"%", "%."+name.replace('.',''),))
        results = self.sql_fetchall(query)
        return [x[0] for x in results]

    def getByIssuer(self, issuer_id):
        """
        """
        query = ("SELECT graphene_json FROM %s " % (self.__tablename__) +
                 "WHERE issuer_id = ?",
                (issuer_id, ))
        results = self.sql_fetchall(query)
        return [x[0] for x in results]

    def getBySymbol(self, symbol):
        """
        """
        symbol = symbol.upper()
        return self.getById(symbol, is_symbol=True)

    def getById(self, asset_id, is_symbol=False):
        """
        """
        if not is_symbol:
            query = ("SELECT graphene_json from %s " % (self.__tablename__) +
                     "WHERE asset_id=?",
                     (asset_id, ))
        else:
            query = ("SELECT graphene_json from %s " % (self.__tablename__) +
                     "WHERE symbol=?",
                     (asset_id, ))

        row = self.sql_fetchone(query)
        if not row:
            return None

        return json.loads(row[0])

    def add(self, asset_id, symbol, graphene_json):
        """ Add an asset

           :param str asset_id: Asset ID (1.3.X)
           :param str symbol: Asset Symbol
           :param dict graphene_json: Dump from blockchain
        """
        if self.getById(asset_id):
            raise ValueError("Asset already in storage")
        if not('issuer' in graphene_json):
            raise KeyError("Missing issuer key")
        issuer_id = graphene_json['issuer']
        query = ('INSERT INTO %s (symbol, asset_id, issuer_id, graphene_json) ' % self.__tablename__ +
                 'VALUES (?, ?, ?, ?)',
                 (symbol.upper(), asset_id, issuer_id, json.dumps(graphene_json)))
        self.sql_execute(query)

    def countEntries(self):
        query = (("SELECT COUNT(id) from %s " % self.__tablename__),)
        op = self.sql_fetchone(query)
        return int(op[0])

    def update(self, asset_id, graphene_json):
        """ Add an account

           :param str account_name: Account name
        """
        query = ('UPDATE %s SET graphene_json = ? ' % self.__tablename__ +
                 'WHERE asset_id = ?',
                 (json.dumps(graphene_json), asset_id))
        self.sql_execute(query)

    def deleteBySymbol(self, symbol):
        """ Delete the record identified as `symbol`

           :param str symbol: Asset Symbol ('bts')
        """
        self.sql_execute(
            "DELETE FROM %s " % (self.__tablename__) +
            "WHERE symbol=?",
             (symbol.upper())
        )

    def deleteById(self, asset_id):
        """ Delete the record identified as `asset_id`

           :param str asset_id: Asset ID ('1.2.0')
        """
        self.sql_execute(
            "DELETE FROM %s " % (self.__tablename__) +
            "WHERE asset_id=?",
            (asset_id)
        )

    def wipe(self):
        """ Delete ALL entries
        """
        query = ("DELETE FROM %s " % (self.__tablename__),)
        self.sql_execute(query)


from bitshares.storage import BitsharesStorage

class BitsharesStorageExtra(BitsharesStorage):

    def __init__(self, path, create=True, **kwargs):
        log.info("Initializing storage %s create: %s" %(path, str(create)))
        super(BitsharesStorageExtra, self).__init__(path=path, create=create, **kwargs)

        # Extra storages
        self.accountStorage = Accounts(path, mustexist = not(create))
        if not self.accountStorage.exists_table() and create:
            self.accountStorage.create_table()

        #self.labelStorage = Label(path)
        #if not self.labelStorage.exists_table() and create:
        #    self.labelStorage.create_table()

        self.assetStorage = Assets(path, mustexist=not(create))
        if not self.assetStorage.exists_table() and create:
            self.assetStorage.create_table()

        self.historyStorage = History(path, mustexist=not(create))
        if not self.historyStorage.exists_table() and create:
            self.historyStorage.create_table()

        self.remotesStorage = Remotes(path, mustexist=not(create))
        if not self.remotesStorage.exists_table() and create:
            self.remotesStorage.create_table()

        self.gatewayStorage = ExternalHistory(path)
        if not self.gatewayStorage.exists_table() and create:
            self.gatewayStorage.create_table()
