import logging
import warnings

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import mean_squared_error, r2_score

warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


def train_decision_tree(df, max_depth=None):
    X = df.drop("Price", axis=1)
    y = df['Price']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=1)

    model = DecisionTreeRegressor(max_depth=max_depth)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    logger.info("Decision Tree - Train: %.4f, Test: %.4f", model.score(X_train, y_train), model.score(X_test, y_test))

    return model, {'MSE': mse, 'R2': r2}, X_test, y_test, y_pred


def train_random_forest(df, n_estimators, max_depth=None):
    X = df.drop("Price", axis=1)
    y = df['Price']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=1)

    model = RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    logger.info("Random Forest - Train: %.4f, Test: %.4f", model.score(X_train, y_train), model.score(X_test, y_test))

    return model, {'MSE': mse, 'R2': r2}, X_test, y_test, y_pred


def clean(df):
    df = df.drop_duplicates()

    df[['Brand', 'Model']] = df['Name'].str.extract(r'\d{4} (\w+) (\w+)')

    columns_to_drop = ["Seller Comments", "Location", "Brand", "Name"]
    for column in columns_to_drop:
        if column in df.columns:
            df.drop(column, axis=1, inplace=True)

    df = df.dropna(axis=1, how='all')

    overall_mode = df.mode().iloc[0]
    for column in df.columns[df.isnull().any()]:
        if df[column].isnull().any():
            df[column].fillna(overall_mode[column], inplace=True)

    return df


def encode(df):
    if 'Owner_Type' in df.columns:
        owner_dic = {'first': 3, 'second': 2, 'third': 1}
        df['Owner_Type'] = df['Owner_Type'].map(owner_dic).fillna(0)

    if 'Fuel_Type' in df.columns:
        fuel_dic = {'petrol': 1, 'diesel': 2, 'cng': 3, 'lpg': 4, 'electric': 5, 'petrol + petrol': 1, 'diesel + diesel': 2, 'petrol + cng': 6}
        df['Fuel_Type'] = df['Fuel_Type'].map(fuel_dic).fillna(7)

    if 'Transmission' in df.columns:
        trans_dic = {'automatic': 1, 'manual': 2}
        df['Transmission'] = df['Transmission'].map(trans_dic).fillna(7)

    le = LabelEncoder()
    df['Model'] = le.fit_transform(df['Model'])

    return df


def train(df):
    X = df.drop("Price", axis=1)
    Y = df['Price']

    X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2, random_state=1)

    rf = RandomForestRegressor(n_estimators=30)
    rf.fit(X_train, Y_train)
    return rf


def model_call(train_df, user_input):
    train_df = clean(train_df)
    train_df = encode(train_df)
    predictor = train(train_df)

    features_to_input = list(user_input.keys())
    filtered_user_input = {feature: user_input[feature] for feature in features_to_input if feature in train_df.columns}

    user_df = pd.DataFrame([filtered_user_input])
    user_df = encode(user_df)

    predicted_price = predictor.predict(user_df)

    logger.info("Predicted Price: %s", predicted_price[0])
    return predicted_price[0]
