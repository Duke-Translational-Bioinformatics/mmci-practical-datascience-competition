from rest_framework.views import APIView
from rest_framework.response import Response
import re
import json
from sklearn import metrics
import requests
import io
import time
import pandas as pd
import numpy as np
import os
from rest_framework.exceptions import APIException


class CustomException(APIException):

    def __init__(self, request):
        """
        A custom Django Rest Framework exception to pass request failures through the endpoint /api/azure/
        :param request: requests.models.Response
        """
        self.status_code = request.status_code
        self.default_code = request.reason
        self.default_detail = request.text
        self.code = request.reason
        self.detail = json.loads(request.text)

class NoInputException(APIException):
    status_code = 400
    default_code = 'Bad Request'
    default_detail = 'All fields in Google Sheets must be complete'


class NoResponsewithResponseException(APIException):
    status_code = 409
    default_code = 'Conflict'
    default_detail = 'It appears that your model contains the predictor variable readmitted, please remove and rerun'


class MultipleModelNoSupportException(APIException):
    status_code = 409
    default_code = 'Conflict'
    default_detail = 'It appears that your web service exposes more than one model, please expose only one model'


class ScoreData(APIView):
    """
    Endpoint to send user submitted model through to Azure
    """
    def post(self, request, format=None):
        """
        Returns results from scoring procedure via Azure
        :param request:
        :param format:
        :return:
        """
        inputtt = request.data
        if ((inputtt['apikey'] == '') or
                (inputtt['url'] == '') or
                (inputtt['scoredvariablename'] == '') or
                (inputtt['datascientist'] == '')):
            raise NoInputException()
        api_key = inputtt['apikey']
        url = inputtt['url']
        rvp = inputtt['scoredvariablename']
        ds = inputtt['datascientist']
        output_name = re.sub(r'\s+', '', re.sub('[^A-Za-z\.]+', ' ', ds)).lower() + ".csv"
        results = get_model_results(api_key, url, rvp, output_name)
        print(results)
        return Response(results)

def _check_err(request_object):
    """
    A function to look through a reqeust object to inspect for errors before proceeding
    :param request_object:
    :return: request response
    """
    if request_object.status_code > 300:
        raise CustomException(request_object)
    else:
        return request_object


def get_model_results(api_key=None,
                      url=None,
                      response_variable_prediction=None,
                      output_name=None):
    """
    A utility function that takes as input, microsoft azure learning studio model criteria and returns an auc with
    the held back data.
    :param api_key: str: Azure ML Studio model api_key
    :param url: str: Azure ML Studio BATCH URL
    :param response_variable_prediction: Variable name that contains the predicted probability (limited to [0,1]).
    :param output_name:
    :return: dict: of particular importance is the auc key
    """
    storage_account_name = os.environ.get('storage_account_name')  # Replace this with your Azure Storage Account name
    storage_account_key = os.environ.get('storage_account_key')  # Replace this with your Azure Storage Key
    storage_container_name = os.environ.get('storage_container_name')  # Replace this with your Azure Storage Container name
    connection_string = "DefaultEndpointsProtocol=https;AccountName=" + storage_account_name + ";AccountKey=" + storage_account_key

    payload = {

        "Inputs": {

            "input1": {"ConnectionString": connection_string,
                       "RelativeLocation": "/" + storage_container_name + "/diabetic-holdback.csv"},
        },

        "Outputs": {

            "output1": {"ConnectionString": connection_string,
                        "RelativeLocation": "/" + storage_container_name + '/' + output_name},
        },
        "GlobalParameters": {
        }
    }

    body = str.encode(json.dumps(payload))
    headers = {"Content-Type": "application/json", "Authorization": ("Bearer " + api_key)}

    #submit the job for processing:
    process_request = _check_err(requests.post(url + "?api-version=2.0", body, headers=headers))
    job_id = process_request.text[1:-1]

    # start the job
    job_request = _check_err(requests.post(url + "/" + job_id + "/start?api-version=2.0", "", headers=headers))

    check_url = url + "/" + job_id + "?api-version=2.0"
    #is the job done?
    while True:
        print("Checking the job status...")
        # If you are using Python 3+, replace urllib2 with urllib.request in the follwing code
        req = _check_err(requests.get(check_url, headers={"Authorization": ("Bearer " + api_key)}))

        result = json.loads(req.text)
        status = result["StatusCode"]
        if (status == 0 or status == "NotStarted"):
            print("Job " + job_id + " not yet started...")
        elif (status == 1 or status == "Running"):
            print("Job " + job_id + " running...")
        elif (status == 2 or status == "Failed"):
            CustomException(req)
            break
        elif (status == 3 or status == "Cancelled"):
            CustomException(req)
            break
        elif (status == 4 or status == "Finished"):
            print("Job " + job_id + " finished!")
            break
        time.sleep(1)
    results = result["Results"]
    if len(results) > 1:
        raise MultipleModelNoSupportException()
    for outputName in results:
        result_blob_location = results[outputName]
        sas_token = result_blob_location["SasBlobToken"]
        base_url = result_blob_location["BaseLocation"]
        relative_url = result_blob_location["RelativeLocation"]
        url3 = base_url + relative_url + sas_token
        response = _check_err(requests.get(url3))
        urlData = response.content
        rawData = pd.read_csv(io.StringIO(urlData.decode('utf-8')))
        print('Columns on scored data: ' + rawData.columns)
        missing_cols = np.sum(rawData[response_variable_prediction].isnull())
        if missing_cols>0:
            print('Missing values found, dropping ' + str(missing_cols))
            rawData = rawData[~rawData[response_variable_prediction].isnull()]
        auc = metrics.roc_auc_score(np.asarray(rawData['admitted']),
                                                 np.asarray(rawData[response_variable_prediction]))


        if auc > 0.95:
            print(auc)
            raise NoResponsewithResponseException()

        output = {
            'job_id': job_id,
            'check_url': check_url,
            'blob_score_results': results,
            'auc': auc

        }
    return output

