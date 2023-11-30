import pandas as pd
import numpy as np
import warnings
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler
import joblib


from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, r2_score
import seaborn as sns
import matplotlib.pyplot as plt


warnings.filterwarnings('ignore')



def train_decision_tree(df, max_depth=None):
    X = df.drop("Price", axis=1)
    y = df['Price']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=1)

    model = DecisionTreeRegressor(max_depth=max_depth)
    model.fit(X_train, y_train)

    # Evaluate on the test set
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    print("{Decision Tree}")
    # print(f"Decision Tree (max_depth={max_depth}) MSE:", mse)
    # print(f"Decision Tree (max_depth={max_depth}) R^2:", r2)

    print("Accuracy on Training set: ",model.score(X_train,y_train))
    print("Accuracy on Testing set: ",model.score(X_test,y_test))

    return model, {'MSE': mse, 'R2': r2}, X_test, y_test, y_pred

def train_random_forest(df, n_estimators, max_depth=None):
    X = df.drop("Price", axis=1)
    y = df['Price']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=1)

    model = RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth)
    model.fit(X_train, y_train)

    # Evaluate on the test set
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    print("{Random forest}")
    # print(f"Random Forest (n_estimators={n_estimators}, max_depth={max_depth}) MSE:", mse)
    # print(f"Random Forest (n_estimators={n_estimators}, max_depth={max_depth}) R^2:", r2)

    print("Accuracy on Training set: ",model.score(X_train,y_train))
    print("Accuracy on Testing set: ",model.score(X_test,y_test))

    return model, {'MSE': mse, 'R2': r2}, X_test, y_test, y_pred
#plot 

# DATA CLEANING
def clean(df):

    df.drop_duplicates
    #rows=df.shape[0]

    # Split 'Name' into 'Brand' and 'Model' columns
    df[['Brand', 'Model']] = df['Name'].str.extract(r'\d{4} (\w+) (\w+)')

    # Check if each column exists in the DataFrame before dropping it
    columns_to_drop = ["Seller Comments", "Location", "Brand","Name"]

    for column in columns_to_drop:
        if column in df.columns:
            df.drop(column, axis=1, inplace=True)

    # Drop all columns that have all null values 
    df = df.dropna(axis=1, how='all')

    # df['Price']=df['Price'].astype(int)
    # df.isnull().sum()

    # Calculate the mode for the entire DataFrame (excluding null values)
    overall_mode = df.mode().iloc[0]

    # Iterate through columns with null values
    for column in df.columns[df.isnull().any()]:
        if df[column].isnull().any():
            # Fill null values in the current column with the overall mode
            df[column].fillna(overall_mode[column], inplace=True)

    return df


# DATA ENCODING      
def encode(df):
        
    if 'Owner_Type' in df.columns:
        owner_dic = {'first':3,'second':2,'third':1}
        df['Owner_Type'] = df['Owner_Type'].map(owner_dic).fillna(0)

        
    if 'Fuel_Type' in df.columns:
        fuel_dic = {'petrol':1,'diesel':2,'cng':3,'lpg':4,'electric':5,'petrol + petrol':1,'diesel + diesel':2,'petrol + cng':6}
        df['Fuel_Type'] = df['Fuel_Type'].map(fuel_dic).fillna(7)


    if 'Transmission' in df.columns:
        trans_dic = {'automatic':1,'manual':2}
        df['Transmission'] = df['Transmission'].map(trans_dic).fillna(7)

    le = LabelEncoder()
    df['Model']=le.fit_transform(df['Model'])   

    return df

# model training 
def train(df):
 
    X = df.drop("Price",axis=1)   #independent variables
    Y= df['Price'] #dependent variables        

    X_train,X_test,Y_train,Y_test=train_test_split(X,Y,test_size=0.2,random_state=1)

    rf = RandomForestRegressor(n_estimators=30)
    rf.fit(X_train, Y_train)
    predictor=rf 
    return predictor
    #y_pred= rf.predict(X_test)

# def model_call(train_df, user_input):
     
#     # Clean web scraped data 
#     train_df = clean(train_df)
#     # Encode the cleaned data
#     train_df = encode(train_df)
#     # Train the data 
#     print("Training data:\n")
#     print(train_df)
#     predictor = train(train_df)

#     # Clean and encode user's data accordingly
#     user_df = pd.DataFrame([user_input])
#     # Split 'Name' into 'Brand' and 'Model' columns
#     user_df[['Brand', 'Model']] = user_df['Name'].str.extract(r'\d{4} (\w+) (\w+)')
#     user_df = encode(user_df)

#     # Get columns that are in train_df
#     common_columns = set(train_df.columns)
    
#     print("before filter columns:\n")
#     print(user_df)

#     # Filter user_df to keep only common columns
#     user_df = user_df.filter(items=common_columns)

#     print(user_df)
#     print("after filter columns:\n")
#     user_df.drop("Price", axis=1, inplace=True)
#     print("after drop price column:\n")
#     print(user_df)

#     # Make a price prediction for user's data 
#     predicted_price = predictor.predict(user_df)

#     # Output the predicted price
#     return predicted_price[0]

def model_call(train_df, user_input):
     
    # clean web scraped data 
    train_df=clean(train_df)
    # encode the cleaned data
    train_df=encode(train_df)
    # train the  data 
    predictor=train(train_df)
   
    #print(train_df)
    #clean user's data accordingly
    features_to_input = list(user_input.keys())

    # Filter the features that are in both the DataFrame and user input
    filtered_user_input = {feature: user_input[feature] for feature in features_to_input if feature in train_df.columns}

    #converting into dataframe
    user_df=pd.DataFrame([filtered_user_input])
    
    # encode the user's data
    user_df=encode(user_df)
    # Make a price prediction for user's data 
    #print(user_df)
    predicted_price = predictor.predict(user_df)

    print(f"Predicted Price: {predicted_price[0]}")
    return predicted_price[0]
    

# # variables 
# csv_path="/Users/shriyays/Desktop/CAPSTONE/working_code/FINAL_CODE/cars_temp.csv"
# train_df = pd.read_csv(csv_path)
# train_df=pd.DataFrame(train_df)
# user_input = {
#     'Brand': 'Honda',
#     'Model': 'City',
#     'Location': 'Pune',
#     'Year': 2015,
#     'Kilometers_Driven':54999,
#     'Fuel_Type': 'petrol',
#     'Transmission': 'manual',
#     'Owner_Type': 'second',
#     'Mileage': 17.57,
#     'Engine': 1193,
#     'Power': 117,
#     'Seats': 5,  # Assuming you meant 4 seats (the original value was empty)
#     'Seller_Comments': 'good car=4.19L',  # Assuming this is a seller comment
# }

# output = main(train_df,user_input)
# print(output)



"""
DATATYPES FOR WEB SCRAPER CODE TO RETURN A DF TO PASS HERE
Name                  object
Location              object
Year                   int64
Kilometers_Driven      int64
Owner_Type             int64
Fuel_Type             object
Power                  int64
Price                float64
"""











