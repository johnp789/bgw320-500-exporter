"""bg320-500 exporter"""
import os
import time

from bs4 import BeautifulSoup
from prometheus_client import start_http_server
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily, REGISTRY
import requests


ROUTER_ADDR = os.getenv("ROUTER_ADDR", "dsldevice.attlocal.net")


def parse_uptime_str(uptime_str: str) -> int:
    split_str = uptime_str.split(":")
    return (
        int(split_str[3])
        + 60 * int(split_str[2])
        + 60 * 60 * int(split_str[1])
        + 24 * 60 * 60 * int(split_str[0])
    )


def device_info():
    req = requests.get(f"http://{ROUTER_ADDR}/cgi-bin/sysinfo.ha", timeout=5)
    soup = BeautifulSoup(req.text, "html.parser")

    model_number = soup.find(
        text="Model Number"
    ).next_element.next_element.string.strip()

    serial_number = soup.find(
        text="Serial Number"
    ).next_element.next_element.string.strip()

    software_version = soup.find(
        text="Software Version"
    ).next_element.next_element.string.strip()

    uptime_str = soup.find(
        text="Time Since Last Reboot"
    ).next_element.next_element.string.strip()

    uptime = parse_uptime_str(uptime_str)

    return (model_number, serial_number, software_version, uptime)


class CustomCollector:
    def collect(self):
        labels = [
            "model_number",
            "serial_number",
            "software_version",
            "ip_address",
        ]
        model_number, serial_number, software_version, uptime = device_info()

        req = requests.get(
            f"http://{ROUTER_ADDR}/cgi-bin/broadbandstatistics.ha", timeout=5
        )
        soup = BeautifulSoup(req.text, "html.parser")

        broadband_connection = soup.find(
            text="Broadband Connection"
        ).next_element.next_element.string.strip()

        broadband_ip_address = soup.find(
            text="Broadband IPv4 Address"
        ).next_element.next_element.string.strip()

        label_values = [
            model_number,
            serial_number,
            software_version,
            broadband_ip_address,
        ]

        gauge = GaugeMetricFamily("broadband_up", "Broadband is up", labels=labels)
        if broadband_connection == "Up":
            broadband_up_gauge = 1
        else:
            broadband_up_gauge = 0
        gauge.add_metric(label_values, broadband_up_gauge)
        yield gauge

        counter = CounterMetricFamily("uptime_total", "Uptime in seconds")
        counter.add_metric([], int(uptime))
        yield counter

        receive_bytes = soup.find(text="Receive Bytes").next_element.next_element.string

        counter = CounterMetricFamily("receive_bytes_total", "Received bytes")
        counter.add_metric([], int(receive_bytes))
        yield counter

        receive_packets = soup.find(
            text="Receive Packets"
        ).next_element.next_element.string

        counter = CounterMetricFamily(
            "receive_packets_total",
            "Received packets",
        )
        counter.add_metric([], int(receive_packets))
        yield counter

        transmit_bytes = soup.find(
            text="Transmit Bytes"
        ).next_element.next_element.string

        counter = CounterMetricFamily(
            "transmit_bytes_total",
            "Transmitted bytes",
        )
        counter.add_metric([], int(transmit_bytes))
        yield counter

        transmit_packets = soup.find(
            text="Transmit Packets"
        ).next_element.next_element.string

        counter = CounterMetricFamily(
            "transmit_packets_total",
            "Transmitted packets",
        )
        counter.add_metric([], int(transmit_packets))
        yield counter


REGISTRY.register(CustomCollector())

if __name__ == "__main__":
    start_http_server(
        port=int(os.getenv("PORT") or 8000), addr=os.getenv("ADDR", "0.0.0.0")
    )
    while True:
        time.sleep(1)
