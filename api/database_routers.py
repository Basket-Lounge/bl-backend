import random 


class DBRouter:
    """
    A router to control all database operations for the 'auth' and 'contenttypes' apps.
    Routes reads to the replica database and writes to the primary database.
    """

    def db_for_read(self, model, **hints):
        """
        Direct read operations to the replica database.
        """
        return random.choice(["replica1", "replica2"])

    def db_for_write(self, model, **hints):
        """
        Direct write operations to the primary database.
        """
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if either involved model is in the routed apps.
        """
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Ensure migrations for routed apps only occur in the primary database.
        """
        return "default" if db == "default" else None
    

class TestDBRouter:
    """
    A database router for testing environments.
    Forces all queries to use the default database during tests.
    """

    def db_for_read(self, model, **hints):
        """
        Direct all read operations to the default database.
        """
        return "default"

    def db_for_write(self, model, **hints):
        """
        Direct all write operations to the default database.
        """
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow all model relations in the default database.
        """
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Ensure migrations run only on the default database.
        """
        return db == "default"