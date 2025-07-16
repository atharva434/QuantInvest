from django.shortcuts import render, redirect
from django.http import HttpResponseNotFound
from django.db import connection
from .forms import ExpiryForm

def expiry_list_view(request):
    # Call stored function to get all expiry records
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM view_expiries()")
        columns = [col[0] for col in cursor.description]
        expiries = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return render(request, 'expiry_list.html', {'expiries': expiries})


def expiry_add_view(request):
    if request.method == 'POST':
        form = ExpiryForm(request.POST)
        if form.is_valid():
            month = form.cleaned_data['month']
            expiry_type = form.cleaned_data['expiry_type']
            expiry_date = form.cleaned_data['expiry_date']
            with connection.cursor() as cursor:
                cursor.execute("CALL insert_expiry(%s, %s, %s)", [month, expiry_type, expiry_date])
            return redirect('expiry')
    else:
        form = ExpiryForm()
    return render(request, 'expiry_form.html', {'form': form, 'action': 'Add'})


def expiry_update_view(request, id):
    # Fetch record from DB using view_expiries function
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM view_expiries() WHERE id = %s", [id])
        row = cursor.fetchone()
        if not row:
            return HttpResponseNotFound("Expiry record not found.")
        columns = [col[0] for col in cursor.description]
        record = dict(zip(columns, row))

    if request.method == 'POST':
        form = ExpiryForm(request.POST)
        if form.is_valid():
            month = form.cleaned_data['month']
            expiry_type = form.cleaned_data['expiry_type']
            expiry_date = form.cleaned_data['expiry_date']
            with connection.cursor() as cursor:
                cursor.execute("CALL update_expiry(%s, %s, %s, %s)", [id, month, expiry_type, expiry_date])
            return redirect('expiry')
    else:
        form = ExpiryForm(initial=record)

    return render(request, 'expiry_form.html', {'form': form, 'action': 'Update'})


def expiry_delete_view(request, id):
    with connection.cursor() as cursor:
        cursor.execute("CALL delete_expiry(%s)", [id])
    return redirect('expiry')