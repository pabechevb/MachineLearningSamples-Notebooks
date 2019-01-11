#!/usr/bin/env python
# coding: utf-8

# # Models in Azure Machine Learning Package for Forecasting
# This notebook demonstrates how to use the forecasting models available in Azure Machine Learning Package for Forecasting (AMLPF). The following types of models are covered:  
# 
# * Univariate Time Series Models
# * Machine Learning Models
# * Model Union 
# 
# We will also briefly talk about model performance evaluation. 

# ### Import dependencies for this sample

# In[1]:


import warnings
# Squash warning messages for cleaner output in the notebook
warnings.showwarning = lambda *args, **kwargs: None

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor

from ftk import TimeSeriesDataFrame
from ftk.data import load_dominicks_oj_features
from ftk.models import (Arima, SeasonalNaive, Naive, ExponentialSmoothing, 
                        RegressionForecaster, ForecasterUnion)

print('imports done')


# ## Load data
# Since the focus of this notebook is the AMLPF models, we load a preprocessed dataset with prepared features. Some features are from the [original dataset from Dominick's Finer Foods](https://research.chicagobooth.edu/kilts/marketing-databases/dominicks), and others are generated by the featurization transformers in AMLPF. Please see the sample notebooks on transformers for feature engieering tips with AMLPF. 

# In[2]:


train_features_tsdf, test_features_tsdf = load_dominicks_oj_features()
nseries = train_features_tsdf.groupby(train_features_tsdf.grain_colnames).ngroups
nstores = len(train_features_tsdf.index.get_level_values(train_features_tsdf.group_colnames[0]).unique())
print('Grain column names are {}'.format(train_features_tsdf.grain_colnames))
print('{} time series in the data frame.'.format(nseries))
print('Group column names are {}'.format(train_features_tsdf.group_colnames))
print('{} stores/groups in the data frame.'.format(nstores))
train_features_tsdf.head()


# The data contains 249 different combinations of store and brand in a data frame. Each combination defines its own time series of sales. 
# 
# The difference between _grain_ and _group_ is that _grain_ usually identifies a single time series in the raw data (without multi-horizon features), while _group_ can contain multiple time series in the raw data. As will be shown later, internal package functions use group to build a single model from multiple time series if the user believes this grouping helps improve model performance. By default, group is set to be equal to grain, and a single model is built for each grain. 

# ## Univariate Time Series Models
# 
# A univariate time series is a sequence of observations of the same variable recorded over time, ususally at regular time intervals. Univaraite time series models analyze the temporal patterns, e.g. trend, seasonality, in the target variable to forecast future values of the target variable.  
# The following univariate models are available in AMLPF. 
# 
# * The **Naive** forecasting algorithm uses the actual target variable value of the last period as the forecasted value of the current period.
# 
# * The **Seasonal Naive** algorithm uses the actual target variable value of the same time point of the previous season as the forecasted value of the current time point. Some examples include using the actual value of the same month of last year to forecast months of the current year; use the same hour of yesterday to forecast hours today. 
# 
# * The **Exponential Smoothing (ES)** algorithm generates forecasts by computing the weighted averages of past observations, with the weights decaying exponentially as the observations get older. 
# 
# * The **AutoRegressive Integrated Moving Average (ARIMA)** algorithm captures the autocorrelation in time series data. For more information about ARIMA, see [this link](https://en.wikipedia.org/wiki/Autoregressive_integrated_moving_average)

# Since the univariate models only utilizes the sales values over time, we extract the sales values column to save computation time and space. 

# In[3]:


train_tsdf =  TimeSeriesDataFrame(train_features_tsdf[train_features_tsdf.ts_value_colname],
                                  grain_colnames=['store', 'brand'],
                                  time_colname='WeekLastDay',
                                  ts_value_colname='Quantity',
                                  group_colnames='store')
test_tsdf =  TimeSeriesDataFrame(test_features_tsdf[test_features_tsdf.ts_value_colname],
                                 grain_colnames=['store', 'brand'],
                                 time_colname='WeekLastDay',
                                 ts_value_colname='Quantity',
                                 group_colnames='store')
train_tsdf.head()


# Next, set the frequency and seasonality parameters for univariate models.   
# **Frequency** is the time interval at which the observations are recorded, e.g. daily, weekly, monthly. The frequency of the Dominick's data is weekly, ended on every Wednesday. The frequency of a dataset can be obtained by calling the `get_frequency_dict` method of a TimeSeriesDataFrame.  
# **Seasonality** is a periodic pattern in time series data with a fixed and known period. This pattern is usually associated with some aspect of the calendar. For example, a time series with quarterly frequency presents repeated pattern every four quarters, then the seasonality of this time series is 4. The Dominick's data don't present any strong seasonality pattern. Here we assume a yearly seasonality, which is 52 (weeks). The seasonality of a dataset can be obtained by calling the `get_seasonality_dict` of a TimeSeriesDataFrame.

# In[4]:


series_freq = 'W-WED'
series_seasonality = 52


# ### Initialize Univariate Models

# In[5]:


naive_model = Naive(freq=series_freq)

seasonal_naive_model = SeasonalNaive(freq=series_freq, 
                                     seasonality=series_seasonality)

# Initialize Exponential Smoothing model
# Don't allow multiplicative trend since it can lead to instability
es_model = ExponentialSmoothing(freq=series_freq,
                                allow_multiplicative_trend=False)

arima_order = [2, 1, 0]
arima_model = Arima(series_freq, arima_order)


# ### Train Univariate Models
# The estimators in AMLPF follow the same API as scikit-learn estimators: a `fit` method for model training and a `predict` method for generating forecasts.  
# Since these models are all univariate models, one model is fit on each grain of the data. Using AMLPF, all 249 models can be fit with just one function call.  

# In[6]:


naive_model_fitted = naive_model.fit(train_tsdf)
seasonal_naive_model_fitted = seasonal_naive_model.fit(train_tsdf)
es_model_fitted = es_model.fit(train_tsdf)
arima_model_fitted = arima_model.fit(train_tsdf)


# ### Forecast/Predict with Univariate Models
# Once the models are trained, you can generate forecast by calling the `predict` method with the testing/scoring/new data. Similar to the fit method, you can create predictions for all 249 series in the testing dataset with one call to the `predict` function. 

# In[7]:


naive_model_forecast = naive_model_fitted.predict(test_tsdf)
seasonal_naive_model_forecast = seasonal_naive_model_fitted.predict(test_tsdf)
es_model_forecast = es_model_fitted.predict(test_tsdf)
arima_model_forecast = arima_model_fitted.predict(test_tsdf)
arima_model_forecast.head()


# The output of the `predict` method is a [ForecastDataFrame](https://docs.microsoft.com/en-us/python/api/ftk.dataframe_forecast.forecastdataframe?view=azure-ml-py-latest) with point and distribution forecast columns. 

# ## Machine Learning Models
# 
# In addition to traditional univariate models, Azure Machine Learning Package for Forecasting also enables you to create machine learning models for forecasting. 
# 

# ### RegressionForecaster
# 
# The [RegressionForecaster](https://docs.microsoft.com/en-us/python/api/ftk.models.regression_forecaster.regressionforecaster?view=azure-ml-py-latest)  function wraps scikit-learn regression estimators so that they can be trained on [TimeSeriesDataFrame](https://docs.microsoft.com/en-us/python/api/ftk.dataframe_ts.timeseriesdataframe?view=azure-ml-py-latest). The wrapped forecasters have the following functionalities:
# 1. Put each `group` of data into the same model, so that it can learn one model for a group of series that are deemed similar and can be pooled together. One model for a group of series often uses the data from longer series to improve forecasts for short series. 
# 2. Create one-hot encoding for categorical features, if `internal_featurization` is set to `True`, because scikit-learn estimators can generally only accept numeric features.
# 3. Create `grain` and `horizon` features, if both `internal_featurization` and `make_grain_features` are set to `True`.   
# 
# Here we demonstrate a couple of regression models. You can substitute these models for any other models in sckit-learn that support regression.

# ### Initialize Machine Learning Models

# In[8]:


# Set "make_grain_features" to False, because our data already contain grain and horizon features
random_forest_model = RegressionForecaster(estimator=RandomForestRegressor(),
                                           make_grain_features=False)
boosted_trees_model = RegressionForecaster(estimator=GradientBoostingRegressor(),
                                           make_grain_features=False)


# ### Train Machine Learning Models

# In[9]:


#random_forest_model_fitted = random_forest_model.fit(train_features_tsdf)
boosted_trees_model_fitted = boosted_trees_model.fit(train_features_tsdf)


# ### Forecast/Predict with Machine Learning Models

# In[10]:


#random_forest_forecast = random_forest_model_fitted.predict(test_features_tsdf)
boosted_trees_forecast = boosted_trees_model_fitted.predict(test_features_tsdf)
boosted_trees_forecast.head()


# In[11]:


print(type(boosted_trees_forecast))


# In[12]:


_qty = 'Quantity'
_store = 'store'
_brand = 'brand'
_date = 'WeekLastDay'
cols = [_qty, 'PointForecast']
boosted_trees_forecast_out = boosted_trees_forecast[cols]
boosted_trees_forecast_out.to_json()[:1000]


# ## Combine Multiple Models
# 
# The [ForecasterUnion](https://docs.microsoft.com/en-us/python/api/ftk.models.forecaster_union.forecasterunion?view=azure-ml-py-latest) estimator allows you to combine multiple estimators and fit/predict on them using one line of code. Here we combine all the models created above. 

# In[13]:


forecaster_union = ForecasterUnion(
    forecaster_list=[('naive', naive_model), 
                     ('seasonal_naive', seasonal_naive_model), 
                     ('es', es_model), 
                     ('arima', arima_model),
                     ('random_forest', random_forest_model),
                     ('boosted_trees', boosted_trees_model)])
forecaster_union_fitted = forecaster_union.fit(train_features_tsdf)
forecaster_union_forecast = forecaster_union_fitted.predict(test_features_tsdf, retain_feature_column=True)


# ## Performance Evaluation
# 
# Now you can calculate the forecast errors on the test set. You can use the mean absolute percentage error (MAPE) here. MAPE is the mean absolute percent error relative to the actual sales values. The ```calc_error``` function provides a few built-in functions for commonly used error metrics. You can also define your custom error function to calculate other metrics, e.g. MedianAPE, and pass it to the `err_fun` argument.

# In[14]:


def calc_median_ape(y_true, y_pred):
    y_true = np.array(y_true).astype(float)
    y_pred = np.array(y_pred).astype(float)
    y_true_rm_na = y_true[~(np.isnan(y_true) | np.isnan(y_pred))]
    y_pred_rm_na = y_pred[~(np.isnan(y_true) | np.isnan(y_pred))]
    y_true = y_true_rm_na
    y_pred = y_pred_rm_na
    if len(y_true) == 0:
        # if there is no entries left after removing na data, return np.nan
        return(np.nan)
    y_true_rm_zero = y_true[y_true != 0]
    y_pred_rm_zero = y_pred[y_true != 0]
    if len(y_true_rm_zero) == 0:
        # if all values are zero, np.nan will be returned.
        return(np.nan)
    ape = np.abs((y_true_rm_zero - y_pred_rm_zero) / y_true_rm_zero) * 100
    median_ape = np.median(ape)
    return median_ape


# In[15]:


forecaster_union_MAPE = forecaster_union_forecast.calc_error(err_name='MAPE',
                                                             by='ModelName')
forecaster_union_MedianAPE = forecaster_union_forecast.calc_error(err_name='MedianAPE', 
                                                                  err_fun=calc_median_ape,
                                                                  by='ModelName')
all_model_errors = forecaster_union_MAPE.merge(forecaster_union_MedianAPE, on='ModelName')
all_model_errors.sort_values('MedianAPE')


# The machine learning models are able to take advantage of the added features and the similarities between series to get better forecast accuracy.
