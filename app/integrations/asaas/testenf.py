import requests

url = "https://api-sandbox.asaas.com/v3/invoices"

payload = {
    "taxes": {
        "retainIss": False,
        "iss": 0,
        "pis": 0,
        "cofins": 0,
        "csll": 0,
        "inss": 0,
        "ir": 0
    },
    "payment": "pay_4i6y8i499dl4j6nw",
    "customer": "cus_000007754021",
    "serviceDescription": "Suporte técnico remoto em software de telefonia da portaria referente ao mês de Março/2026.",
    "observations": "Suporte técnico remoto em software de telefonia da portaria referente ao mês de Março/2026.",
    "value": 100,
    "effectiveDate": "2026-04-04",
    "municipalServiceCode": "1.07",
    "municipalServiceName": "Suporte técnico em informática"
}

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "access_token": "$aact_hmlg_000MzkwODA2MWY2OGM3MWRlMDU2NWM3MzJlNzZmNGZhZGY6OjQwMWZkNGNhLTRiZTgtNDcwNC04NmFhLTUzOTQwYmIyOGQ3Yzo6JGFhY2hfMjI1NTIxOTctNWQxMi00OTViLTg4NjItMTgxYWI1ZGM5Zjg5"
}

response = requests.post(url, json=payload, headers=headers)
print(response.text)
