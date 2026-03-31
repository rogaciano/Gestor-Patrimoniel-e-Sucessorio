"""
Validadores de CPF e CNPJ para Django
"""
from django.core.exceptions import ValidationError
import re


def validate_cpf(value):
    """
    Valida CPF (Cadastro de Pessoas Físicas) brasileiro
    Formato aceito: 000.000.000-00 ou 00000000000
    """
    # Remove caracteres não numéricos
    cpf = re.sub(r'[^0-9]', '', value)
    
    # Verifica se tem 11 dígitos
    if len(cpf) != 11:
        raise ValidationError('CPF deve conter 11 dígitos.')
    
    # Verifica CPFs inválidos conhecidos (todos iguais)
    if cpf in ['00000000000', '11111111111', '22222222222', '33333333333',
               '44444444444', '55555555555', '66666666666', '77777777777',
               '88888888888', '99999999999']:
        raise ValidationError('CPF inválido.')
    
    # Validação do primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    if int(cpf[9]) != digito1:
        raise ValidationError('CPF inválido.')
    
    # Validação do segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    if int(cpf[10]) != digito2:
        raise ValidationError('CPF inválido.')


def validate_cnpj(value):
    """
    Valida CNPJ (Cadastro Nacional de Pessoa Jurídica) brasileiro
    Formato aceito: 00.000.000/0000-00 ou 00000000000000
    """
    # Remove caracteres não numéricos
    cnpj = re.sub(r'[^0-9]', '', value)
    
    # Verifica se tem 14 dígitos
    if len(cnpj) != 14:
        raise ValidationError('CNPJ deve conter 14 dígitos.')
    
    # Verifica CNPJs inválidos conhecidos
    if cnpj in ['00000000000000', '11111111111111', '22222222222222']:
        raise ValidationError('CNPJ inválido.')
    
    # Validação do primeiro dígito verificador
    multiplicadores1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * multiplicadores1[i] for i in range(12))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    if int(cnpj[12]) != digito1:
        raise ValidationError('CNPJ inválido.')
    
    # Validação do segundo dígito verificador
    multiplicadores2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * multiplicadores2[i] for i in range(13))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    if int(cnpj[13]) != digito2:
        raise ValidationError('CNPJ inválido.')
