from typing import Dict, Any

class PolyurethaneCalculator:
    """
    Продвинутый калькулятор для расчета стехиометрии и рецептур 
    полиуретановых форполимеров и 1К герметиков.
    """
    
    # Физико-химические константы
    NCO_MW = 42.02  # г/экв (молярная масса изоцианатной группы)
    OH_MW = 17.01   # г/экв (молярная масса гидроксильной группы)
    MDI_MW = 250.25 # г/моль (4,4'-MDI)
    IPDI_MW = 222.28 # г/моль (IPDI)
    HDI_MW = 168.20  # г/моль (HDI)

    @staticmethod
    def calculate_formulation(
        polyol_mw: float, 
        polyol_func: float, 
        diisocyanate_mw: float, 
        nco_index: float, 
        polyol_mass: float = 100.0
    ) -> Dict[str, Any]:
        """
        Расчет базовой стехиометрии NCO-форполимера (используется для симуляции DOE).
        """
        # 1. Эквивалентные массы
        polyol_ev = polyol_mw / polyol_func
        iso_ev = diisocyanate_mw / 2.0  # Для диизоцианатов f=2
        
        # 2. Эквиваленты функциональных групп
        oh_eq = polyol_mass / polyol_ev
        nco_eq = oh_eq * nco_index
        
        # 3. Массы компонентов
        iso_mass = nco_eq * iso_ev
        total_mass = polyol_mass + iso_mass
        
        # 4. Свободный NCO
        excess_nco_eq = nco_eq - oh_eq
        free_nco_mass = excess_nco_eq * PolyurethaneCalculator.NCO_MW
        free_nco_percent = (free_nco_mass / total_mass) * 100
        
        # 5. Hard Segment Content (HSC) - массовая доля жесткого сегмента
        hsc_percent = (iso_mass / total_mass) * 100
        
        return {
            "Polyol_Mass_g": round(polyol_mass, 2),
            "Isocyanate_Mass_g": round(iso_mass, 2),
            "Total_Prepolymer_Mass_g": round(total_mass, 2),
            "Theoretical_Free_NCO_Percent": round(free_nco_percent, 2),
            "NCO_OH_Index": nco_index,
            "Hard_Segment_Content_Percent": round(hsc_percent, 2)
        }

    @classmethod
    def calculate_full_batch(
        cls,
        target_batch_mass: float,
        polyol_mw: float,
        polyol_func: float,
        diisocyanate_mw: float,
        nco_oh_ratio: float,
        plasticizer_frac: float,
        filler_frac: float,
        additive_frac: float = 0.02,
        aldimine_eq_weight: float = 267.0 # Эквивалентная масса алдимина (из патента Sika)
    ) -> Dict[str, float]:
        """
        Расчет полной лабораторной навески (batch) для синтеза герметика.
        Возвращает массы компонентов в граммах для заданного объема замеса.
        """
        # 1. Доля полимерной матрицы (полиол + изоцианат) в готовом продукте
        polymer_frac = 1.0 - (plasticizer_frac + filler_frac + additive_frac)
        polymer_mass = target_batch_mass * polymer_frac
        
        # 2. Алгебраический расчет масс полиола и изоцианата
        polyol_ev = polyol_mw / polyol_func
        iso_ev = diisocyanate_mw / 2.0
        
        # Решаем систему уравнений:
        # m_polyol + m_iso = polymer_mass
        # (m_iso / iso_ev) / (m_polyol / polyol_ev) = nco_oh_ratio
        m_polyol = polymer_mass / (1 + nco_oh_ratio * (iso_ev / polyol_ev))
        m_iso = polymer_mass - m_polyol
        
        # 3. Расчет скрытого отвердителя (Алдимины)
        oh_eq = m_polyol / polyol_ev
        nco_eq = m_iso / iso_ev
        excess_nco_eq = nco_eq - oh_eq
        free_nco_percent = (excess_nco_eq * cls.NCO_MW / polymer_mass) * 100
        
        # Масса алдимина (стехиометрия 1:1 по эквивалентам, с коэфф. 0.88 из DOE)
        aldimine_eq = excess_nco_eq * 0.88 
        aldimine_mass = aldimine_eq * aldimine_eq_weight
        
        # 4. Формируем итоговый рецепт
        batch_recipe = {
            "Target_Batch_Mass_g": target_batch_mass,
            "Polyol_Mass_g": round(m_polyol, 2),
            "Isocyanate_Mass_g": round(m_iso, 2),
            "Plasticizer_Mass_g": round(target_batch_mass * plasticizer_frac, 2),
            "Filler_Mass_g": round(target_batch_mass * filler_frac, 2),
            "Additives_Mass_g": round(target_batch_mass * additive_frac, 2),
            "Aldimine_Mass_g": round(aldimine_mass, 2),
            "Theoretical_Free_NCO_Percent": round(free_nco_percent, 2)
        }
        
        return batch_recipe