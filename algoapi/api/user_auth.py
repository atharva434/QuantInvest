from .forms import ClientRegistrationForm,UserInfo
from django.contrib.auth import authenticate,login
from django.shortcuts import render,redirect
from django.contrib.auth.models import User, Group
import requests
from .forms import ClientRegistrationFrontendForm
from django.conf import settings


# def client_registration(request):
#     if request.method == 'POST':
#         regform = ClientRegistrationForm(request.POST)
#         userinfo = UserInfo(request.POST)

#         if userinfo.is_valid() and regform.is_valid():
#             user = userinfo.save(commit=False)
#             raw_password = userinfo.cleaned_data.get("password")  # securely access password
#             user.set_password(raw_password)  # hash the password
#             user.save()

#             clientForm = regform.save(commit=False)
#             clientForm.user = user
#             clientForm.save()

#             # Add user to Client group
#             my_patient_group, _ = Group.objects.get_or_create(name='UserAccounts')
#             my_patient_group.user_set.add(user)

#             # Log in the user
#             login(request, user)
#             return redirect("client_login")
#     else:
#         regform = ClientRegistrationForm()
#         userinfo = UserInfo()

#     return render(request, 'client_registration.html')# Replace with the client dashboard URL


def client_registration(request):
    if request.method == 'POST':
        form = ClientRegistrationFrontendForm(request.POST)
        if form.is_valid():
            payload = {
                "username": form.cleaned_data['username'],
                "password": form.cleaned_data['password'],
                "acc_name": form.cleaned_data['acc_name'],
                "acc_provider": form.cleaned_data['acc_provider'],
                "app_key": form.cleaned_data['app_key'],
                "secret_key": form.cleaned_data['secret_key'],
            }

            # Replace with your backend API URL
            backend_url = settings.BACKEND_BASE_URL+ "/api/register/"  # or use your prod/staging domain
            response = requests.post(backend_url, json=payload)

            if response.status_code == 201:
                return redirect('client_login')
            else:
                form.add_error(None, f"Registration failed: {response.json()}")
    else:
        form = ClientRegistrationFrontendForm()

    return render(request, 'client_registration.html', {'form': form})



def client_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        session_token = request.POST.get("session_token")

        # Send data to backend login API
        try:
            response = requests.post(
                settings.BACKEND_BASE_URL+ "/api/login/",
                json={
                    "username": username,
                    "password": password,
                    "session_token": session_token,
                }
            )
            data = response.json()
            if response.status_code == 200:
                # Store session or token as needed
                request.session["auth_token"] = data.get("token")
                request.session["username"] = data.get("username")
                request.session["session_token"] = session_token
                print("response", response.status_code)
                return redirect("open_positions")  # or any protected page
            else:
                error = data.get("error", "Invalid credentials.")

                return render(request, "client_login.html", {"error": error})
        except Exception as e:
            print("exception", e)
            return render(request, "client_login.html", {"error": str(e)})

    return render(request, "client_login.html")


def get_client_info(user):
    try:
        client = user.clients.first()
        return client.app_key, client.secret_key
    except:
        return {"error": "No client details found for this user"}