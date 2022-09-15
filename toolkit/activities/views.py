import json
import time
from http import HTTPStatus

from django.core.exceptions import ObjectDoesNotExist

from core.bitrix24.bitrix24 import ActivityB24, ImopenlineB24, DealB24
from core.models import Portals
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from pybitrix24 import Bitrix24

from activities.models import Activity
from settings.models import SettingsPortal


@csrf_exempt
def install(request):
    """View for install application in portal."""
    member_id = request.POST.get('member_id')
    activity_code = request.POST.get('code')

    portal: Portals = get_object_or_404(Portals, member_id=member_id)
    portal.check_auth()

    activity = get_object_or_404(Activity, code=activity_code)
    try:
        activity_b24 = ActivityB24(portal, obj_id=None)
        result = activity_b24.install(activity.build_params())
    except RuntimeError as ex:
        return JsonResponse({
            'result': 'False',
            'error_name': ex.args[0],
            'error_description': ex.args[1]})
    return JsonResponse({'result': result})


@csrf_exempt
def uninstall(request):
    """View for uninstall application in portal."""
    member_id = request.POST.get('member_id')
    activity_code = request.POST.get('code')

    portal: Portals = get_object_or_404(Portals, member_id=member_id)
    portal.check_auth()

    try:
        activity_b24 = ActivityB24(portal, obj_id=None, code=activity_code)
        result = activity_b24.uninstall()
    except RuntimeError as ex:
        return JsonResponse({
            'result': 'False',
            'error_name': ex.args[0],
            'error_description': ex.args[1]})
    return JsonResponse({'result': result})


@csrf_exempt
def operator_add(request):
    """View for activity copy products."""
    initial_data = _get_initial_data_copy_products(request)
    portal, settings_portal = _create_portal(initial_data)
    _check_initial_data_copy_products(portal, initial_data)
    try:
        line = ImopenlineB24(portal, 0)
        result = line.crm_chat_user_add(
            initial_data.get('crm_entity_type'),
            initial_data.get('crm_entity'),
            initial_data.get('user_id'),
        )
    except Exception as ex:
        _response_for_bp(
            portal,
            initial_data['event_token'],
            'Ошибка при добавлении в чат CRM сущности.',
            return_values={'result': f'Error: {ex.args[0]}'},
        )
        return HttpResponse(status=HTTPStatus.OK)
    _response_for_bp(
        portal,
        initial_data['event_token'],
        'Успех. Оператор добавлен в чат.',
        return_values={'result': f'Ok: {result = }'},
    )
    return HttpResponse(status=HTTPStatus.OK)


@csrf_exempt
def pause(request):
    """View for activity pause."""
    initial_data = _get_initial_data_pause(request)
    portal, settings_portal = _create_portal(initial_data)
    _check_initial_data_pause(portal, initial_data)
    time.sleep(initial_data['pause'])
    _response_for_bp(
        portal,
        initial_data['event_token'],
        f'Успех. Пауза в {initial_data["pause"]} секунд.',
    )
    return HttpResponse(status=HTTPStatus.OK)


@csrf_exempt
def field_update(request):
    """View for activity field in deal update."""
    initial_data = _get_initial_data_field_update(request)
    portal, settings_portal = _create_portal(initial_data)
    _check_initial_data_field_update(portal, initial_data)
    try:
        deal = DealB24(portal, initial_data.get('deal_id'))
        deal.update(initial_data.get('field_code'), initial_data.get(
            'field_value'))
    except Exception as ex:
        _response_for_bp(
            portal,
            initial_data['event_token'],
            'Ошибка. Невозможно обновить поле в сделке.',
            return_values={'result': f'Error: {ex.args[0]}'},
        )
        return HttpResponse(status=HTTPStatus.OK)
    _response_for_bp(
        portal,
        initial_data['event_token'],
        f'Успех. Полю в сделке {initial_data["field_code"]} присвоено '
        f'новое значение {initial_data["field_value"]}.',
    )
    return HttpResponse(status=HTTPStatus.OK)


def _create_portal(initial_data):
    """Method for create portal."""
    try:
        portal = Portals.objects.get(member_id=initial_data['member_id'])
        portal.check_auth()
        settings_portal = SettingsPortal.objects.get(portal=portal)
        return portal, settings_portal
    except ObjectDoesNotExist:
        return HttpResponse(status=HTTPStatus.BAD_REQUEST)


def _get_initial_data_copy_products(request):
    """Method for get initial data from Post request activity copy products."""
    if request.method != 'POST':
        return HttpResponse(status=HTTPStatus.BAD_REQUEST)
    user = request.POST.get('properties[user_id]')
    user_id = user.split('_')[1] if 'user' in user else user
    return {
        'member_id': request.POST.get('auth[member_id]'),
        'event_token': request.POST.get('event_token'),
        'crm_entity_type': request.POST.get('properties[crm_entity_type]'),
        'crm_entity': request.POST.get('properties[crm_entity]') or 0,
        'user_id': user_id,
    }


def _get_initial_data_pause(request):
    """Method for get initial data from Post request activity pause."""
    if request.method != 'POST':
        return HttpResponse(status=HTTPStatus.BAD_REQUEST)
    return {
        'member_id': request.POST.get('auth[member_id]'),
        'event_token': request.POST.get('event_token'),
        'pause': request.POST.get('properties[pause]'),
    }


def _get_initial_data_field_update(request):
    """Method for get initial data from Post request activity field in deal
    update."""
    if request.method != 'POST':
        return HttpResponse(status=HTTPStatus.BAD_REQUEST)
    return {
        'member_id': request.POST.get('auth[member_id]'),
        'event_token': request.POST.get('event_token'),
        'field_code': request.POST.get('properties[field_code]'),
        'field_value': request.POST.get('properties[field_value]'),
        'deal_id': request.POST.get('properties[deal_id]') or 0,
    }


def _check_initial_data_copy_products(portal, initial_data):
    """Method for check initial data activity copy products."""
    try:
        initial_data['user_id'] = int(initial_data['user_id'])
        initial_data['crm_entity'] = int(initial_data['crm_entity'])
    except Exception as ex:
        _response_for_bp(
            portal,
            initial_data['event_token'],
            'Ошибка. Проверьте входные данные.',
            return_values={'result': f'Error: {ex.args[0]}'},
        )
        return HttpResponse(status=HTTPStatus.OK)


def _check_initial_data_pause(portal, initial_data):
    """Method for check initial data activity pause."""
    try:
        initial_data['pause'] = int(initial_data['pause'])
    except Exception as ex:
        _response_for_bp(
            portal,
            initial_data['event_token'],
            'Ошибка. Проверьте входные данные.',
        )
        return HttpResponse(status=HTTPStatus.OK)


def _check_initial_data_field_update(portal, initial_data):
    """Method for check initial data activity field in deal update."""
    try:
        initial_data['deal_id'] = int(initial_data['deal_id'])
    except Exception as ex:
        _response_for_bp(
            portal,
            initial_data['event_token'],
            'Ошибка. Проверьте входные данные.',
            return_values={'result': f'Error: {ex.args[0]}'},
        )
        return HttpResponse(status=HTTPStatus.OK)


def _response_for_bp(portal, event_token, log_message, return_values=None):
    """Method for send parameters in bp."""
    bx24 = Bitrix24(portal.name)
    bx24._access_token = portal.auth_id
    method_rest = 'bizproc.event.send'
    params = {
        'event_token': event_token,
        'log_message': log_message,
        'return_values': return_values,
    }
    bx24.call(method_rest, params)
