from decimal import Decimal
from typing import List, Dict

class PartitionEngine:
    """
    Motor de cálculo para simulação de partilha de bens.
    Baseado no Código Civil (Comunhão Parcial como padrão).
    """

    @staticmethod
    def calculate_partition(
        regime_bens: str,
        ativos_comuns: List[Dict],
        ativos_particulares: List[Dict],
        numero_herdeiros: int,
        tem_conjuge: bool,
        ativos_comuns_indiretos: List[Dict] = None,
        ativos_particulares_indiretos: List[Dict] = None
    ) -> Dict:
        """
        Calcula partilha de bens conforme legislação brasileira.
        
        Args:
            regime_bens: Regime de bens do casamento (CP, CU, SB, PF)
            ativos_comuns: Ativos comuns adquiridos durante o casamento (propriedade direta)
            ativos_particulares: Ativos particulares (propriedade direta)
            numero_herdeiros: Número de herdeiros necessários
            tem_conjuge: Se existe cônjuge sobrevivente
            ativos_comuns_indiretos: Ativos comuns via Holdings (opcional)
            ativos_particulares_indiretos: Ativos particulares via Holdings (opcional)
            
        Returns:
            Dict com meação, monte-mor, quota por herdeiro, etc.
        """
        
        # Inicializa ativos indiretos como listas vazias se não fornecidos
        if ativos_comuns_indiretos is None:
            ativos_comuns_indiretos = []
        if ativos_particulares_indiretos is None:
            ativos_particulares_indiretos = []
        
        # 1. Soma dos montantes (diretos + indiretos)
        total_comum = sum((item['valor'] for item in ativos_comuns), Decimal('0')) + \
                      sum((item['valor'] for item in ativos_comuns_indiretos), Decimal('0'))
        
        total_particular = sum((item['valor'] for item in ativos_particulares), Decimal('0')) + \
                           sum((item['valor'] for item in ativos_particulares_indiretos), Decimal('0'))

        
        resumo = {
            "monte_mor_bruto": total_comum + total_particular,
            "meacao_conjuge": Decimal('0.00'),
            "heranca_total": Decimal('0.00'),
            "legitima": Decimal('0.00'),
            "disponivel": Decimal('0.00'),
            "valor_por_herdeiro": Decimal('0.00')
        }

        # 2. Lógica de Meação (Direito de Família)
        # Na Comunhão Parcial, o cônjuge tem direito à metade dos bens comuns
        if regime_bens == 'CP':
            resumo["meacao_conjuge"] = total_comum / 2
            # A herança é composta pela outra metade dos comuns + bens particulares
            resumo["heranca_total"] = (total_comum / 2) + total_particular
        
        elif regime_bens == 'CU': # Comunhão Universal
            resumo["meacao_conjuge"] = (total_comum + total_particular) / 2
            resumo["heranca_total"] = (total_comum + total_particular) / 2
            
        elif regime_bens == 'SB': # Separação de Bens
            resumo["meacao_conjuge"] = Decimal('0.00')
            resumo["heranca_total"] = total_comum + total_particular

        # 3. Divisão da Herança (Sucessão)
        # A Legítima é sempre 50% da herança para herdeiros necessários
        resumo["legitima"] = resumo["heranca_total"] / 2
        resumo["disponivel"] = resumo["heranca_total"] / 2
        
        # 4. Cálculo por Cabeça (Simplificado)
        if numero_herdeiros > 0:
            # Em cenários reais, o cônjuge pode concorrer na herança nos bens particulares
            # Aqui fazemos a divisão simples do total da herança entre os herdeiros
            resumo["valor_por_herdeiro"] = resumo["heranca_total"] / numero_herdeiros

        return resumo
