from pymongo import MongoClient
from bson.objectid import ObjectId

class AnimalShelter(object):
    """ CRUD operations for Animal collection in MongoDB """

    def __init__(self, username, password):
        # Initializing the MongoClient. This helps to 
        # access the MongoDB databases and collections.
        # This is hard-wired to use the aac database, the 
        # animals collection, and the aac user.
        # Definitions of the connection string variables are
        # unique to the individual Apporto environment.
        #
        # You must edit the connection variables below to reflect
        # your own instance of MongoDB!
        #
        # Connection Variables
        #
        USER = username #'aacuser'
        PASS = password # 'SNHU1234'
        HOST = 'nv-desktop-services.apporto.com'
        PORT = 34339
        DB = 'AAC'
        COL = 'animals'
        #
        # Initialize Connection
        #
        self.client = MongoClient('mongodb://%s:%s@%s:%d/?authSource=admin' % (USER,PASS,HOST,PORT))
        self.database = self.client['%s' % (DB)]
        self.collection = self.database['%s' % (COL)]

# Complete this create method to implement the C in CRUD.
    def create(self, data):
        if data is not None:
                #Added a try statemnt for error handling
                try:
                    self.database.animals.insert_one(data)  # data should be dictionary            
                    return True
                except Exception as e:
                    print(f"Insert failed: {e}")
                    return False
        else:
            raise Exception("Data parameter is empty")


# Create method to implement the R in CRUD.
    def read(self, data):
         if data is not None:
            try:
                query = self.database.animals.find(data)
                return list(query)
            except Exception as e:
                print(f"Query failed: {e}")
         else:
             print('Query failed')
             return []

# A method to update (U) in crud
    def update(self,query,newData):
        if query is not None and newData is not None:
            try:
                #Using only update__many bescause it can be used to just update one document.
                result = self.database.animals.update_many(query,newData)
                return result.modified_count
            except Exception as e:
                print(f"Update failed: {e}")
        else:
             print('Update failed, unable to update')
             return []
        
# A method to delete documents in the database
    def delete(self,data):
        if data is not None:
            try:
                valuesDeleted = self.database.animals.delete_many(data)
                return valuesDeleted.deleted_count
            except Exception as e:
                print('Delete failed: {e}')
                return 0
        else:
            raise Exception("Filter parameter is empty")