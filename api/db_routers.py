# api/db_routers.py
class AuthRouter:
    """
    A router to control all database operations on models in the
    auth and contenttypes applications.
    """
    route_app_labels = {'auth', 'contenttypes', 'admin', 'sessions'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'default'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'default'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Allow relations only between models in the same database
        db1 = hints.get('instance') and self.db_for_write(obj1.__class__)
        db2 = hints.get('instance') and self.db_for_write(obj2.__class__)
        if db1 and db2:
            return db1 == db2
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.route_app_labels:
            return db == 'default'
        return None


class CustomerRouter:
    """
    A router to control all database operations on models in the api app.
    """
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'api':
            return 'customers'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'api':
            return 'customers'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Allow relations only between models in the same database
        if obj1._meta.app_label == 'api' and obj2._meta.app_label == 'api':
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Only allow migrations for default database
        if app_label == 'api':
            return False  # Don't migrate API models to any SQL database
        return None  # Let other routers decide