from .models import Printer, SystemSettings
from django.utils.translation import gettext_lazy as _
from escpos.printer import Usb, Dummy     # Further infos: https://python-escpos.readthedocs.io/en/latest/user/methods.html
from datetime import datetime
import os, pwd, sys
import usb.core, usb.util, usb._lookup as _lu
from .bluetooth.adapter import *
from .bluetooth.device import *
from .bluetooth.dbus_tools import *
import time
import socket
from operator import itemgetter


def list_installed_USB_printers():
    listInstalled = list(Printer.objects.filter(printType = 'Usb').values())
    for i in listInstalled:
        try:
            p = Usb(i['printIdVendor'], i['printIdProduct'], 0, i['printIn_ep'], i['printOut_ep'])
            p.open()
            i['printStatus'] = 1
            p.close()
        except Exception as error:
            i['printStatus'] = 0
    return listInstalled


def list_available_USB_printers():
    devices = usb.core.find(find_all=True)
    listAvailable = []
    for dev in devices:
        dict = {}
        for cfg in dev:
            pass
            for intf in cfg:
                ''' filter for InterfaceClass = 0x7 (Printer) '''
                if (intf.bInterfaceClass) == 7:
                    dict.update({
                        'printName': f"{usb.util.get_string(dev, dev.iManufacturer)}, {usb.util.get_string(dev, dev.iProduct)}",
                        'printType': 'Usb',
                        'printIdVendor': dev.idVendor,
                        'printIdProduct': dev.idProduct,
                        'printMacAddress': None,                        
                        'printStatus': 2,
                        })
                    for end in intf:
                        if usb.util.endpoint_direction(end.bEndpointAddress) == usb.util.ENDPOINT_IN:
                            dict.update({
                                'printIn_ep': end.bEndpointAddress,
                            })
                        if usb.util.endpoint_direction(end.bEndpointAddress) == usb.util.ENDPOINT_OUT:
                            dict.update({
                                'printOut_ep': end.bEndpointAddress,
                            })
        listAvailable.append(dict) if dict else None

    return listAvailable


def clean_USB_list(items: list[dict], keys: set[str]):
    existed: set[tuple[str | int]] = set()
    listCleaned: list[dict] = []

    for item in items:
        body = item
        values = tuple(body[key] for key in keys)
        if values not in existed:
            listCleaned.append(item)
            existed.add(values)

    return listCleaned


def list_all_USB_devices():
    listInstalled = list_installed_USB_printers()
    listAvailable = list_available_USB_printers()
    listFinal = []
    if not (listInstalled and listAvailable):
        listFinal = listInstalled + listAvailable
        listRaw = listInstalled + listAvailable
    else:
        listRaw = sorted((listInstalled + listAvailable), key=itemgetter('printName', 'printIdVendor', 'printIdProduct', 'printStatus'))
        listFinal = clean_USB_list(items=listRaw, keys={'printName', 'printIdVendor', 'printIdProduct'})

    return listFinal


def install_USB_printer(data):
    data = eval(data.replace("'", "\""))
    print('data', type(data))
    try:
        newPrinter = Printer(
            printName = data['printName'],
            printType = 'Usb',
            printIdVendor = data['printIdVendor'],
            printIdProduct = data['printIdProduct'],
            printIn_ep = data['printIn_ep'],
            printOut_ep = data['printOut_ep'],
            printMacAddress = None,
        )
        newPrinter.save()
        return True
    except Exception as error:
        print(type(error).__name__, error)
        return False


def delete_USB_printer(pk):
    try:
        Printer.objects.filter(pk=pk).delete()
        return True
    except Exception as error:
        print(type(error).__name__, error)
        return False
    

def get_printers(printerList):
    printers_ = []
    for i in printerList:
        if i.printType == 'Usb':
            try:
                p = Usb(i.printIdVendor, i.printIdProduct, 0, i.printIn_ep, i.printOut_ep,)
                p.open()
                printers_.append({i.printName: p})
            except Exception as error:
                print(type(error).__name__, error)
                printers_.append({i.printName: None})

        if i.printType == 'BT':
            #s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            for x in range(3): # 3 attempts
                s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
                #s.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
                #s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
                try:
                    s.connect((i.printMacAddress, 1))
                    break
                except Exception as error:
                    print(type(error).__name__, error)
                    s = None
                time.sleep(1)
            printers_.append({i.printName: s})
    return printers_


def print_order(savedOrder):
    printerList = list({p['prodQuery'].prodclassQuery.printQuery for p in savedOrder if p['prodQuery'].prodclassQuery.printQuery})
    printers_ = get_printers(printerList)
    #print('printers: ', printers_)
    for order in savedOrder:
        if order['prodQuery'].prodclassQuery.printQuery:
            printName = order['prodQuery'].prodclassQuery.printQuery.printName
            printType = order['prodQuery'].prodclassQuery.printQuery.printType
            printer = next((p.get(printName) for p in printers_ if p.get(printName)), None)
            d = Dummy()
            #d.buzzer(times=2, duration=4)
            d.set(font="a", height=2, align="left", bold=False, double_height=True, double_width=False)
            d.textln('-' * 32)
            d.ln(1)
            d.textln(str(datetime.now().strftime("%m.%d.%Y %H:%M")) + '  Order#: ' + str(order['poOrder'].id))
            d.ln(1)
            d.textln('User: ' + str(order['poOrder'].orderUser) + '  Table: ' + str(order['poOrder'].orderTable))
            d.ln(1)
            d.textln(order['prodQuery'])
            d.textln('Qty: ' + str(order['poQty']))
            d.ln(2)
            if printType == 'Usb':
                assert printer, ('Usb device not found or cable not plugged in.')
                printer._raw(d.output)
                time.sleep(1)
            elif printType == 'BT':
                assert printer, ('Bluetooth device not found or cable not plugged in.')
                printer.send(d.output)
                time.sleep(1)
    for printer in (list(p.values())[0] for p in printers_):
        printer.close() if printer else None


def print_receipt(orderInstance, savedProdOrder):
    if orderInstance.menuQuery.printQuery:
        printers_ = get_printers([orderInstance.menuQuery.printQuery])
        printName = orderInstance.menuQuery.printQuery.printName
        printType = orderInstance.menuQuery.printQuery.printType
        printer = next((p.get(printName) for p in printers_ if p.get(printName)), None)
        settings = SystemSettings.objects.get()
        total_receipt = sum(prod.poProdPrice for prod in savedProdOrder)
        VAT_dict = {}
        for prod in savedProdOrder:
            VAT_dict[prod.poProdVAT] = VAT_dict.get(prod.poProdVAT, 0) + round(prod.poProdPrice - (prod.poProdPrice/(1+prod.poProdVAT/100)), 2)
        VAT_list = [{VAT: total} for VAT, total in VAT_dict.items()]

        d = Dummy()
        #d.buzzer(times=2, duration=4)
        d.set(font="a", height=2, align="center", bold=False, double_height=True, double_width=False)
        d.ln(1)
        #d.image('static/img/simOrder_logo_96.png')
        if not settings.companyName:
            d.textln('Your Company Name')
        else:
            d.textln(settings.companyName)
        d.set(font="b", height=1, align="center", bold=False, double_height=True, double_width=False)
        for field in [settings.companyAdress1, settings.companyAdress2, settings.companyInfo1, settings.companyInfo2]:
            if field:
                d.textln(field)
        if not settings.taxIdNumber:
            d.textln('Your Tax Number')
        else:
            d.textln(_('Tax Number: ') + settings.taxIdNumber)
        d.textln(str(datetime.now().strftime("%m.%d.%Y %H:%M")))
        d.textln('-' * 42)
        d.set(font="b", height=2, align="center", bold=False, double_height=True, double_width=False)
        for prod in savedProdOrder:
            len_prod = len(str(prod.poProdDescription))
            len_price = len(str(prod.poProdPrice))
            space = max(3, 42 - len_prod - len_price)
            trunc = min(len_prod, 42 - space - len_price)
            d.textln(prod.poProdDescription[:trunc] + (' ' * space) + str(prod.poProdPrice))
            time.sleep(0.1)
        d.textln('-' * 42)
        space = 42 - 6 - len(str(total_receipt))
        d.textln(_('Total:') + (' ' * space) + str(total_receipt))
        d.ln(1)
        for line in VAT_list:
            for vat_rate, amount in line.items():
                space = 42 - 6 - len(str(vat_rate)) - len(str(amount))
                d.textln(_('VAT ') + str(vat_rate) + '% ' + (' ' * space) + str(amount))
        space = 42 - 1 - len(str(savedProdOrder[0].get_poPayMethod_display())) - len(f"{savedProdOrder[0].poPayAmount:.2f}")
        d.textln(str(savedProdOrder[0].get_poPayMethod_display()) + (':') + (' ' * space) + f"{savedProdOrder[0].poPayAmount:.2f}")
        space = 42 - 19 - len(str(savedProdOrder[0].poTransNumber))
        d.textln(_('Transaction Number:') + (' ' * space) + str(savedProdOrder[0].poTransNumber))
        d.ln(5)

        if printType == 'Usb':
            assert printer, ('Usb device not found or cable not plugged in.')
            printer._raw(d.output)
            time.sleep(1)
        elif printType == 'BT':
            assert printer, ('Bluetooth device not found or cable not plugged in.')
            printer.send(d.output)
            time.sleep(1)
        for printer in (list(p.values())[0] for p in printers_):
            printer.close() if printer else None


def statusBTAdapter():
    try:
        dongle = adapter.Adapter()
        return dongle.powered
    except Exception as error:
        print(type(error).__name__, error)
        return None
    

def toggleBTAdapter():
    try:
        dongle = adapter.Adapter()
        if dongle.powered:
            dongle.powered = False
        else:
            dongle.powered = True
        if dongle.pairable:
            dongle.pairable = False
        else:
            dongle.pairable = True
        return True
    except Exception as error:
        print(type(error).__name__, error)
        return False


def list_available_BT_devices():
    try:
        dongle = adapter.Adapter()
        #dongle.hide_duplicates()
        dongle.nearby_discovery() if not dongle.discovering else None
        nearby_devices = dongle.devices
        return nearby_devices
    except Exception as error:
        print(type(error).__name__, error)
        return 'Not able to activate bluetooth adapter'


def list_paired_BT_devices():
    results = []
    mng_objs = dbus_tools.get_managed_objects()
    for obj in mng_objs.values():
        device = obj.get(constants.DEVICE_INTERFACE, {})
        if device.get('Name', None) and device.get('Trusted'):
            #print(device.get('Name'), device.get('Trusted'))
            results.append({
                'Name': device.get('Name') if 'Name' in device else None,
                'Alias': device.get('Alias') if 'Alias' in device else None,
                'Paired': device.get('Paired') if 'Paired' in device else None,
                'Connected': device.get('Connected') if 'Connected' in device else None,
                'Icon': device.get('Icon') if 'Icon' in device else None,
                'Address': device.get('Address') if 'Address' in device else None,
                'UUIDs': device.get('UUIDs') if 'UUIDs' in device else None,
            })
    if results:
        return results
    else:
        return results.append({'Name': 'No Bluetooth printer installed'})


def pair_trust_BT(data):
    try:
        dongle_addr = adapter.list_adapters()[0]
        printer_addr = data['Address']
        printer_ = device.Device(dongle_addr, printer_addr)
        printer_.pair() if not printer_.paired else None
        printer_.trusted = True if not printer_.trusted else printer_.trusted
        return True
    except Exception as error:
        print(type(error).__name__, error)
        return False


def install_BT_printer(data):
    data = eval(data.replace("'", "\""))
    try:
        pair_trust_BT(data)
        newPrinter = Printer(
            printName = data['Name'],
            printType = 'BT',
            printIdVendor = None,
            printIdProduct = None,
            printIn_ep = None,
            printOut_ep = None,
            printMacAddress = data['Address'],
        )
        newPrinter.save()
        return True
    except Exception as error:
        print(type(error).__name__, error)
        return False


def remove_BT(data):
    try:
        dongle_addr = adapter.list_adapters()[0]
        printer_addr = data['Address']
        printer_ = device.Device(dongle_addr, printer_addr)
        printer_path = dbus_tools.get_dbus_path(adapter=dongle_addr, device=printer_.address)
        dongle = adapter.Adapter()
        dongle.remove_device(printer_path)
        return True
    except Exception as error:
        print(type(error).__name__, error)
        return False


def delete_BT_printer(data):
    data = eval(data.replace("'", "\""))
    try:
        remove_BT(data)
        printer_ = Printer.objects.get(printMacAddress = data['Address'])
        printer_.delete()
        return True
    except Exception as error:
        print(type(error).__name__, error)
        return False


