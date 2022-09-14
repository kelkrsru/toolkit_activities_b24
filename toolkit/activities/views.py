import json
from http import HTTPStatus

from django.core.exceptions import ObjectDoesNotExist

from core.bitrix24.bitrix24 import ActivityB24
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

    initial_data = _get_initial_data(request)
    portal, settings_portal = _create_portal(initial_data)
    _check_initial_data(portal, initial_data)
    with open('/root/test.log', 'w', encoding='utf-8') as file:
        file.write(json.dumps(initial_data))
    # smart_process_code = _initial_smart_process(portal, initial_data)
    # smart_process = SmartProcessB24(portal, 0)
    # products = smart_process.get_all_products(smart_process_code,
    #                                           smart_element_id)
    # deal = DealB24(portal, deal_id)
    # keys_for_del = ['id', 'ownerId', 'ownerType']
    # for product in products:
    #     for key in keys_for_del:
    #         del product[key]
    # deal.get_all_products()
    # products += deal.products
    # deal.set_products(products)
    # _response_for_bp(
    #     portal,
    #     initial_data['event_token'],
    #     'Успех. Товары скопированы.',
    #     return_values={'result': f'Ok: {products = }'},
    # )
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


def _get_initial_data(request):
    """Method for get initial data from Post request."""
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


def _check_initial_data(portal, initial_data):
    """Method for check initial data."""
    try:
        initial_data['user_id'] = int(initial_data['user_id'])
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
