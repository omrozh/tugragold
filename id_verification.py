from suds.client import Client


def verify_id(tc_kimlik_no, isim, soyisim, dogum_yili):
    wsdl = "https://tckimlik.nvi.gov.tr/Service/KPSPublic.asmx?op=TCKimlikNoDogrula&wsdl"
    client = Client(wsdl)
    result = client.service.TCKimlikNoDogrula(tc_kimlik_no, isim, soyisim, dogum_yili)
    return result
