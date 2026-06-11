class PolyurethaneCalculator:
    """Калькулятор для расчета полиуретановых рецептур и форполимеров."""
    
    @staticmethod
    def calculate_formulation(polyol_mw, polyol_func, diisocyanate_mw, nco_index=2.0, polyol_mass=100.0):
        """
        Расчет необходимой массы диизоцианата на заданную массу полиола.
        
        Параметры:
        - polyol_mw: молекулярная масса полиола (г/моль)
        - polyol_func: функциональность полиола (обычно 2.0 для диолов)
        - diisocyanate_mw: молекулярная масса диизоцианата (для 4,4'-MDI = 250.25)
        - nco_index: целевое мольное соотношение NCO/OH (например, 2.0)
        - polyol_mass: базовая масса полиола для расчета (г), по умолчанию 100г
        
        Возвращает: dict с массами компонентов и теоретическим % свободных NCO
        """
        # Эквивалентные веса (EV = Mw / функциональность)
        polyol_ev = polyol_mw / polyol_func
        iso_ev = diisocyanate_mw / 2.0  # Для диизоцианатов функциональность всегда 2
        
        # Моли OH групп в заданной массе полиола
        oh_moles = polyol_mass / polyol_ev
        
        # Требуемые моли NCO групп согласно целевому индексу
        required_nco_moles = oh_moles * nco_index
        
        # Необходимая масса изоцианата
        iso_mass = required_nco_moles * iso_ev
        
        # Общая масса получившегося форполимера
        total_mass = polyol_mass + iso_mass
        
        # Расчет теоретического содержания свободных NCO групп (%) в готовом форполимере
        # Избыточные моли NCO = Всего молей NCO - Затраченные на реакцию с OH (1:1)
        excess_nco_moles = required_nco_moles - oh_moles
        # Масса свободных NCO групп (Mw группы NCO = 42.02 г/моль)
        free_nco_mass = excess_nco_moles * 42.02
        free_nco_percent = (free_nco_mass / total_mass) * 100
        
        return {
            "Polyol_Mass_g": round(polyol_mass, 2),
            "Isocyanate_Mass_g": round(iso_mass, 2),
            "Total_Formopolymer_Mass_g": round(total_mass, 2),
            "Theoretical_Free_NCO_Percent": round(free_nco_percent, 2),
            "NCO_OH_Index": nco_index
        }