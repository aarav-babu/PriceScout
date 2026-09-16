"""Persistent account/product storage, independent of the optional ML pipeline."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (Column, DateTime, ForeignKey, MetaData, String, Table,
                        Text, create_engine, insert, select)

metadata = MetaData()
users = Table('public_users', metadata,
              Column('id', String(36), primary_key=True),
              Column('name', String(80), nullable=False),
              Column('email', String(254), nullable=False, unique=True),
              Column('password_hash', Text, nullable=False),
              Column('created_at', DateTime(timezone=True), nullable=False))
products = Table('public_products', metadata,
                 Column('id', String(36), primary_key=True),
                 Column('user_id', String(36), ForeignKey('public_users.id'), nullable=False, index=True),
                 Column('category', String(20), nullable=False),
                 Column('brand', String(60), nullable=False),
                 Column('model', String(100), nullable=False),
                 Column('details', Text, nullable=False),
                 Column('created_at', DateTime(timezone=True), nullable=False))


class AccountStore:
    def __init__(self, url):
        if url.startswith(('postgres://', 'postgresql://')):
            url = 'postgresql+psycopg://' + url.split('://', 1)[1]
        options = {'pool_pre_ping': True}
        if url.startswith('postgresql'):
            options.update(connect_args={'connect_timeout': 10},
                           pool_size=3, max_overflow=1)
        self.engine = create_engine(url, **options)
        # Only creates these two new, namespaced tables. Never changes the
        # existing application's users, listings, or market/model tables.
        metadata.create_all(self.engine)

    def create_user(self, name, email, password_hash):
        user = {'id': str(uuid4()), 'name': name, 'email': email,
                'password_hash': password_hash, 'created_at': datetime.now(timezone.utc)}
        with self.engine.begin() as db:
            db.execute(insert(users).values(**user))
        return user

    def find_user(self, *, email=None, user_id=None):
        criterion = users.c.email == email if email is not None else users.c.id == user_id
        with self.engine.connect() as db:
            return db.execute(select(users).where(criterion)).mappings().first()

    def save_product(self, user_id, category, brand, model, details):
        product = {'id': str(uuid4()), 'user_id': user_id, 'category': category,
                   'brand': brand, 'model': model, 'details': details,
                   'created_at': datetime.now(timezone.utc)}
        with self.engine.begin() as db:
            db.execute(insert(products).values(**product))
        return product

    def list_products(self, user_id):
        with self.engine.connect() as db:
            return list(db.execute(select(products).where(products.c.user_id == user_id)
                                   .order_by(products.c.created_at.desc()).limit(100)).mappings())

    def get_product(self, product_id, user_id):
        with self.engine.connect() as db:
            return db.execute(select(products).where(products.c.id == product_id,
                                                     products.c.user_id == user_id)).mappings().first()
