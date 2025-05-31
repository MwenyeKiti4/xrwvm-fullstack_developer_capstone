# import os
import json
import logging
# from datetime import datetime

# import requests
# from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout
from django.views.decorators.csrf import csrf_exempt
# from django.contrib import messages

from .populate import initiate
from .models import CarMake, CarModel
from .restapis import get_request, analyze_review_sentiments, post_review

# Get an instance of a logger
logger = logging.getLogger(__name__)


def get_cars(request):
    count = CarMake.objects.count()
    if count == 0:
        initiate()

    car_models = CarModel.objects.select_related("car_make")
    cars = [
        {"CarModel": cm.name, "CarMake": cm.car_make.name}
        for cm in car_models
    ]
    return JsonResponse({"CarModels": cars})


@csrf_exempt
def login_user(request):
    """Handle login requests."""
    data = json.loads(request.body)
    username = data.get("userName")
    password = data.get("password")
    user = authenticate(username=username, password=password)

    if user:
        login(request, user)
        return JsonResponse({"userName": username, "status": "Authenticated"})
    return JsonResponse({"userName": username})


def logout_request(request):
    """Handle logout via POST."""
    if request.method == "POST":
        logout(request)
        return JsonResponse({"success": True, "message": "Logged out successfully"})
    return JsonResponse(
        {"success": False, "error": "Invalid request method"}, status=400
    )


@csrf_exempt
def registration(request):
    """Handle user registration."""
    data = json.loads(request.body)
    username = data.get("userName")
    password = data.get("password")
    first_name = data.get("firstName")
    last_name = data.get("lastName")
    email = data.get("email")

    try:
        User.objects.get(username=username)
        return JsonResponse({"userName": username, "error": "Already Registered"})
    except User.DoesNotExist:
        logger.debug("%s is a new user", username)
        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            password=password,
            email=email,
        )
        login(request, user)
        return JsonResponse({"userName": username, "status": "Authenticated"})


def get_dealer_reviews(request, dealer_id):
    """Render reviews for a specific dealer."""
    if dealer_id:
        endpoint = f"/fetchReviews/dealer/{dealer_id}"
        reviews = get_request(endpoint)
        for review in reviews:
            sentiment = analyze_review_sentiments(review["review"])
            review["sentiment"] = sentiment.get("sentiment")
        return JsonResponse({"status": 200, "reviews": reviews})
    return JsonResponse({"status": 400, "message": "Bad Request"})


def get_dealer_details(request, dealer_id):
    """Return dealer details by ID."""
    if dealer_id:
        endpoint = f"/fetchDealer/{dealer_id}"
        dealer = get_request(endpoint)
        return JsonResponse({"status": 200, "dealer": dealer})
    return JsonResponse({"status": 400, "message": "Bad Request"})


def get_dealerships(request, state="All"):
    """Return all dealerships or filter by state."""
    endpoint = "/fetchDealers" if state == "All" else f"/fetchDealers/{state}"
    dealers = get_request(endpoint)
    return JsonResponse({"status": 200, "dealers": dealers})


@csrf_exempt
def add_review(request):
    """Submit a dealer review if user is authenticated."""
    if not request.user.is_anonymous:
        try:
            data = json.loads(request.body)
            post_review(data)
            return JsonResponse({"status": 200})
        except Exception:
            return JsonResponse({"status": 401, "message": "Error in posting review"})
    return JsonResponse({"status": 403, "message": "Unauthorized"})
