import base64
import logging
import requests
import json
from xml.etree import ElementTree as ET

from datetime import datetime, date, timedelta
from dateutil.parser import parse
#from lxml import ET
from io import BytesIO

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement
_logger = logging.getLogger(__name__)


TYPE_FE = [
    ('FACT', 'Factura'),
    ('FESP', 'Factura Especial'),
    ('FCAM', 'Factura Cambiaria'),
    ('NDEB', 'Nota de Débito'),
    ('NCRE', 'Nota de Crédito'),
    ('NABN', 'Nota de Abono'),
    ('FAEX', 'Factura Exportación'),
    ('OTRO', 'Otro')
]


class AccountMove(models.Model):
    _inherit = 'account.move'

    def send_invoice(self):
        if self.journal_id and not self.journal_id.active_fel:
            return
        URL = self.env['ir.config_parameter'].sudo().get_param('url.webservice.fe')
        xml = self._xml()
        _logger.info('*************Infile-XML***************************')
        _logger.info(xml)
        self.write({ 'arch_xml': base64.b64encode( xml ),
                    'sent_arch_xml': xml,
                    'process_status': 'process',
                    'fe_errors': ''
                  })
        headers = self.company_id._get_headers()
        signed_invoice = self._sign_invoice()
        _logger.info('*************Infile-XML signed_invoice***************************')
        _logger.info(signed_invoice)
        #return self.write({ 'arch_xml': base64.b64decode(signed_invoice) })
        _logger.info( 'signed' )
        headers['identificador'] = self.name
        payloads = {
            "nit_emisor": self.company_id.vat.replace("-", ""),
            "correo_copia": self.partner_id.email or self.company_id.fe_other_email,
            "xml_dte": signed_invoice
            }
        response = requests.post(url=URL, json=payloads, headers=headers )
        data = response.json()
        if data['resultado']:
            certification_date = parse( data['fecha'] )
            xml = base64.b64decode( data['xml_certificado'] )
            self.write( {
                            'fe_uuid': data['uuid'],
                            'fe_xml_file': data['xml_certificado'],
                            'arch_xml': xml, 
                            'process_status': 'ok',
                            'fe_serie': data['serie'],
                            'fe_number': data['numero'],
                            'fe_certification_date': certification_date.strftime('%Y-%m-%d %H:%M:%S')
                        } )
        else:
            error_msg = ''
            count = 0
            for error in data['descripcion_errores']:
                count+=1
                error_msg += '%s. %s \n'%(count, error['mensaje_error'])
            self.write( {'fe_errors': error_msg,'process_status': 'fail'} )
            raise UserError(_('%s') %(error_msg))
        return 