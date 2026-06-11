#!/bin/bash

# 1. Автоматически определяем корень проекта (на уровень выше папки со скриптом)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TARGET_DIR="$PROJECT_ROOT/data/01_raw"

# 2. Создаем целевую директорию и переходим в неё
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR" || { echo "❌ Не удалось перейти в $TARGET_DIR"; exit 1; }

echo "📂 Целевая папка: $TARGET_DIR"
echo "Начинаем загрузку TDS..."

# 3. Массив URL и имен файлов
declare -A urls=(
  ["soudaflex_pu35.pdf"]="https://liveoaksupply.com/content/resources/157901PU35-Technical%20Data%20Sheet.pdf"
  ["soudaflex_36fl.pdf"]="https://soudal.com.au/wp-content/uploads/TDS-Soudal-Soudaflex-36FL.pdf"
  ["soudaseal_nep.pdf"]="https://soudal.co.nz/wp-content/uploads/174914-Soudaseal-NEP-v2-TDS-2025-12-16.pdf"
  ["tytan_fill_all_pu.pdf"]="https://tytan-cdn.tytan.com/uploads/sites/19/2025/03/TYTAN20PROFESSIONAL20Fill20All20PU20Foam20Sealant201220Oz_28-10-2022_TDS_en.pdf"
  ["bostik_915.pdf"]="https://www.bostik.com/files/live/sites/shared_bostik/files/documents-brochures/united-states/Documents/TDS/915_tds.pdf"
  ["3m_540.pdf"]="https://multimedia.3m.com/mws/media/2300031O/3m-polyurethane-sealant-540-tds.pdf"
  ["3m_1k_sealer.pdf"]="https://multimedia.3m.com/mws/media/1399548O/3m-1k-general-purpose-polyurethane-sealer-tds-ner.pdf"
  ["sikaflex_construction.pdf"]="https://usa.sika.com/dam/dms/us01/l/pds-cpd-Sikaflex%20Construction%20Sealant-us.pdf"
  ["novol_gravit630_ru.pdf"]="https://xn--e1aaigqeofr.xn--90ais/files/lists/301979/upload/tehnicheskaya-informaciya-novol-gravit-620-630-germetik.pdf"
  ["novol_gravit630_pl.pdf"]="https://zemax.pl/wp-content/uploads/2019/10/ST_9_13_GRAVIT_630.pdf"
  ["mariflex_pu40.pdf"]="https://www.marispolymers.com/files/grmaris/2024-10/MARIFLEX%20PU%2040%20version22_EN.pdf"
  ["murexin_pu40.pdf"]="https://www.murexin.at/app/media/GB/technicaldatasheets/34225_POLYURETHANVERSIEGELUNG%20PU%2040_20250624_094530.pdf"
  ["rubber_fc40.pdf"]="https://therubbercompany.com/wp-content/uploads/2015/09/FC40-Polyurethane-Sealant-Data-Sheet.pdf"
  ["total_seal_pu40.pdf"]="https://www.totalwaterproofingsupplies.com.au/wp-content/uploads/2021/02/total-seal-pu40-data-sheet.pdf"
  ["tikiseal_pu40.pdf"]="https://tikidan-bucket-x720tx.s3.ap-south-1.amazonaws.com/tds/171039701365f29655b71d7.pdf"
  ["bauer_flexible_pu.pdf"]="https://static.netbauer.com/wp-content/uploads/2021/06/EN-TDS_Flexible-PU-Sealant-2.pdf"
  ["boss_pu25.pdf"]="https://www.bossproducts.in/wp-content/uploads/2024/10/tds-boss-pu-25.pdf"
  ["mightyloc_6221.pdf"]="https://www.mightyloc.com/wp-content/uploads/2020/01/TAFTFLEX-6221_TDS-R1.pdf"
  ["quikrete_nonsag.pdf"]="https://www.tccmaterials.com/wp-content/uploads/2020/06/QKnonsagsealantdata.pdf"
  ["loctite_pl.pdf"]="https://datasheets.tdx.henkel.com/LOCTITE-PL-Window-Door--Siding-Polyurethane-Sealant-en_US.pdf"
  ["cemtec_25n.pdf"]="https://cmci.com.sa/images/Upload/product/1384677918.pdf"
  ["tecnopol_mastic_pu.pdf"]="https://www.tecnopolgroup.com/ckfinder/userfiles/files/datasheets/EN/TDS_EN_MASTIC_PU.pdf"
  ["vipro_pu2k.pdf"]="https://proventuss.eu/wp-content/uploads/2025/11/TDS-VI-PRO-PU-2K_EN-V2.pdf"
  ["chemitool_pu40.pdf"]="https://chemitool.com/wp-content/uploads/2023/06/ft_en_ch040_sealbond_PU40_chemitool_rev3.pdf"
  ["fastcoat_pro_pu.pdf"]="https://www.promain.co.uk/amfile/file/download/file/23981/product/34404/"
)

count=0
success_count=0
for filename in "${!urls[@]}"; do
  count=$((count + 1))
  echo -n "[$count/${#urls[@]}] Загрузка: $filename ... "
  
  # Было
  # Скачиваем с таймаутом 30 сек и следованием за редиректами
  # curl -s -L -o "$filename" "${urls[$filename]}" --max-time 30

  # Стало (добавлен -A для маскировки под браузер):
    curl -s -L -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" -o "$filename" "${urls[$filename]}" --max-time 30
  
  # Проверка: файл существует и его размер > 1000 байт (защита от HTML-страниц с ошибкой 404)
  if [ -f "$filename" ] && [ "$(stat -c%s "$filename" 2>/dev/null || echo 0)" -gt 1000 ]; then
    echo "✅ Успешно"
    success_count=$((success_count + 1))
  else
    echo "⚠️ Ошибка (404 или файл слишком мал). Удаляю."
    rm -f "$filename"
  fi
done

echo ""
echo "🎉 Загрузка завершена!"
echo "✅ Успешно скачано файлов: $success_count из ${#urls[@]}"
echo "📁 Итоговое количество PDF в папке: $(ls -1q *.pdf 2>/dev/null | wc -l)"
