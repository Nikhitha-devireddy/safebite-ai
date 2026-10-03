"""
SafeBite AI - Indian Clinical & Regulatory Intelligence Engine
Includes:
1. FSSAI Regulatory & FoSCoS Standards Compliance (14-digit license, veg/non-veg logos, HFSS alerts)
2. Indian Cultural & Religious Dietary Guardrails (Strict Jain, Navratri/Vrat, Shuddh Shakahari, Sattvic)
3. Indian FMCG Adulterant & Masking Detector (Palm oil/Palmolein, Atta vs Maida, Hidden sugar syrups, Class II preservatives)
4. Ayurvedic Viruddha Ahara (Incompatible Food Combinations) Engine
5. Shree Anna (Indian National Millet Mission) Superfood Swap Engine
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from schemas import NutritionFacts, Ingredients, Allergens


class FssaiComplianceEngine:
    """
    Validates Indian food safety compliance against FSSAI (Food Safety and Standards Authority of India)
    Packaging and Labelling Regulations.
    """

    # 14-digit FSSAI FoSCoS license format
    # Digit 1: License type (1 = Central, 2 = State, etc.)
    # Digits 2-3: State code (e.g., 00 to 38)
    # Digits 4-5: Year of registration
    # Digits 6-8: Enrolling authority / Registrar
    # Digits 9-14: Serial registration number
    FSSAI_REGEX = re.compile(r"\b(1\d{13}|2\d{13})\b")

    STATE_CODES = {
        "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
        "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan",
        "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
        "13": "Nagaland", "14": "Manipur", "15": "Mizoram", "16": "Tripura",
        "17": "Meghalaya", "18": "Assam", "19": "West Bengal", "20": "Jharkhand",
        "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
        "27": "Maharashtra", "29": "Karnataka", "30": "Goa", "32": "Kerala",
        "33": "Tamil Nadu", "36": "Telangana", "37": "Andhra Pradesh"
    }

    # FSSAI HFSS (High Fat, Sugar, Salt) Thresholds per 100g (solid foods)
    HFSS_SUGAR_THRESHOLD_G = 10.0      # > 10g per 100g is High Sugar
    HFSS_SODIUM_THRESHOLD_MG = 250.0   # > 250mg per 100g is High Sodium
    HFSS_SAT_FAT_THRESHOLD_G = 4.0     # > 4.0g per 100g is High Saturated Fat

    @classmethod
    def validate_license(cls, raw_text: str) -> Dict[str, Any]:
        """Scans label declaration text or metadata for a valid 14-digit FSSAI license."""
        match = cls.FSSAI_REGEX.search(raw_text)
        if match:
            lic_num = match.group(1)
            lic_type = "FSSAI Central License" if lic_num.startswith("1") else "FSSAI State License"
            state_code = lic_num[1:3]
            state_name = cls.STATE_CODES.get(state_code, "Indian Jurisdiction")
            return {
                "valid": True,
                "license_number": lic_num,
                "license_type": lic_type,
                "registered_state": state_name,
                "formatted_badge": f"🏛️ FSSAI Lic. #{lic_num} ({state_name})",
                "verified_status": "Verified FoSCoS License Format"
            }
        return {
            "valid": False,
            "license_number": None,
            "license_type": "Unverified / Not Detected",
            "registered_state": "Unknown",
            "formatted_badge": "⚠️ FSSAI License Unverified on Label",
            "verified_status": "Missing 14-digit FoSCoS License"
        }

    @classmethod
    def detect_fssai_logos(cls, text: str, ingredients_text: str = "") -> Dict[str, Any]:
        """
        Determines the mandatory FSSAI food category logo:
        - 🟢 Vegetarian (Green dot in green square)
        - 🟤 Non-Vegetarian (Brown dot in brown triangle/square)
        - 🌱 Vegan (FSSAI 2022 Green 'V' with leaf)
        - 🔵 Fortified (+F blue logo)
        """
        combined = f"{text} {ingredients_text}".lower()

        # Non-veg keywords
        non_veg_terms = [
            "chicken", "mutton", "beef", "pork", "fish", "egg", "eggs", "gelatin",
            "meat", "prawn", "crab", "shrimp", "anchovy", "lard", "carmine", "cochineal"
        ]
        has_non_veg = any(re.search(rf"\b{term}\b", combined) for term in non_veg_terms)

        # Dairy terms
        dairy_terms = [
            "milk", "curd", "dahi", "ghee", "butter", "cheese", "paneer", "whey",
            "casein", "caseinate", "cream", "malai", "buttermilk", "chaas", "khoya", "mawa"
        ]
        has_dairy = any(re.search(rf"\b{term}\b", combined) for term in dairy_terms)

        # Fortified terms (+F logo)
        fortified_terms = [
            "fortified", "+f", "vitamin a fortified", "vitamin d fortified", "iron fortified", "folic acid"
        ]
        is_fortified = any(term in combined for term in fortified_terms)

        if has_non_veg:
            logo_type = "NON_VEG"
            logo_badge = "🟤 Non-Vegetarian (FSSAI Mandatory Brown Mark)"
            logo_class = "badge-avoid"
        elif has_dairy:
            logo_type = "VEGETARIAN"
            logo_badge = "🟢 100% Vegetarian (FSSAI Mandatory Green Mark / Lacto-Veg)"
            logo_class = "badge-clear"
        else:
            # Plant-based and no animal/dairy
            logo_type = "VEGAN"
            logo_badge = "🌱 FSSAI Certified Vegan (100% Plant-Based)"
            logo_class = "badge-clear"

        return {
            "logo_type": logo_type,
            "badge": logo_badge,
            "badge_class": logo_class,
            "is_fortified": is_fortified,
            "fortified_badge": "🔵 +F FSSAI Fortified Food (Micronutrient Enriched)" if is_fortified else None
        }

    @classmethod
    def calculate_hfss(cls, nutrition: Optional[NutritionFacts]) -> Dict[str, Any]:
        """Calculates FSSAI High Fat, Sugar, Salt (HFSS) warning thresholds."""
        if not nutrition:
            return {
                "is_hfss": False,
                "level": "UNKNOWN",
                "summary": "Nutrition panel unavailable for HFSS evaluation",
                "flags": []
            }

        flags = []
        sugar = nutrition.sugar_g
        sodium = nutrition.sodium_mg
        sat_fat = nutrition.saturated_fat_g

        if sugar is not None and sugar > cls.HFSS_SUGAR_THRESHOLD_G:
            flags.append(f"High Sugar ({sugar:.1f}g/100g > {cls.HFSS_SUGAR_THRESHOLD_G}g threshold)")
        if sodium is not None and sodium > cls.HFSS_SODIUM_THRESHOLD_MG:
            flags.append(f"High Sodium ({sodium:.0f}mg/100g > {cls.HFSS_SODIUM_THRESHOLD_MG}mg threshold)")
        if sat_fat is not None and sat_fat > cls.HFSS_SAT_FAT_THRESHOLD_G:
            flags.append(f"High Saturated Fat ({sat_fat:.1f}g/100g > {cls.HFSS_SAT_FAT_THRESHOLD_G}g threshold)")

        is_hfss = len(flags) > 0
        if len(flags) >= 2:
            level = "CRITICAL_HFSS"
            summary = "🚨 RED ALERT: High in Multiple Fat, Sugar, or Salt Parameters (FSSAI HFSS Breached)"
        elif len(flags) == 1:
            level = "MODERATE_HFSS"
            summary = f"⚠️ AMBER WARNING: Exceeds FSSAI {flags[0].split()[1]} Threshold"
        else:
            level = "BALANCED"
            summary = "✅ GREEN COMPLIANT: Within FSSAI Recommended Daily Nutritional Thresholds"

        return {
            "is_hfss": is_hfss,
            "level": level,
            "summary": summary,
            "flags": flags,
            "sugar_g": sugar,
            "sodium_mg": sodium,
            "sat_fat_g": sat_fat
        }


class IndianDietaryGuardrail:
    """
    Enforces authentic Indian cultural, religious, and spiritual dietary guidelines:
    - Strict Jain (Anantkay / Non-Root vegetables, no onion, garlic, potato, fungus)
    - Navratri / Ekadashi Vrat Fasting (Sendha Namak only, Kuttu, Singhara, Sabudana)
    - Shuddh Shakahari (Desi Lacto-Vegetarian)
    - Sattvic Ayurvedic Diet (No Tamasic items)
    """

    # Jain strictly forbidden ingredients
    JAIN_ROOT_VEG = [
        "onion", "onions", "pyaaz", "garlic", "lahsun", "potato", "potatoes", "aloo",
        "carrot", "carrots", "gajar", "radish", "mooli", "beetroot", "chukandar",
        "ginger", "adrak", "sweet potato", "shakarkandi", "turnip", "shalgam",
        "onion powder", "garlic powder", "dehydrated onion", "dehydrated garlic"
    ]
    JAIN_OTHER_FORBIDDEN = [
        "mushroom", "mushrooms", "yeast", "khameer", "honey", "madhu", "gelatin",
        "carmine", "alcohol", "wine", "beer", "egg", "meat", "fish"
    ]

    # Vrat / Fasting forbidden ingredients
    VRAT_FORBIDDEN_GRAINS = [
        "wheat", "atta", "maida", "suji", "semolina", "rice", "chawal", "oats", "barley",
        "corn", "maize", "besan", "gram flour", "chana", "lentil", "lentils", "daal",
        "dal", "moong", "urad", "toor", "masoor", "rajma", "chole"
    ]
    VRAT_FORBIDDEN_SEASONINGS = [
        "iodized salt", "table salt", "onion", "garlic", "turmeric", "haldi", "mustard", "sarson"
    ]
    VRAT_PERMITTED = [
        "kuttu", "buckwheat", "singhara", "water chestnut", "rajgira", "amaranth",
        "sabudana", "tapioca", "sendha namak", "rock salt", "jeera", "cumin",
        "kali mirch", "black pepper", "makhana", "foxnut", "peanuts", "coconut", "ghee"
    ]

    @classmethod
    def evaluate_jain(cls, text: str) -> Dict[str, Any]:
        """Evaluates strict Jain compliance."""
        t_low = text.lower()
        violations = []

        for item in cls.JAIN_ROOT_VEG:
            if re.search(rf"\b{item}\b", t_low):
                violations.append(f"Root Vegetable / Kandmool: '{item.title()}' (forbidden in Jain Ahimsa principles)")

        for item in cls.JAIN_OTHER_FORBIDDEN:
            if re.search(rf"\b{item}\b", t_low):
                violations.append(f"Forbidden Non-Jain Item: '{item.title()}' (contains micro-organisms/fermentation/animal byproduct)")

        # Compounded asafoetida (Hing) check (commercial hing is 60-70% maida/wheat flour)
        if "asafoetida" in t_low or "hing" in t_low:
            violations.append("Hing (Asafoetida): Commercial hing is commonly compounded with wheat flour/gum, requiring scrutiny for strict Jain vows.")

        is_safe = len(violations) == 0
        return {
            "compliant": is_safe,
            "violations": violations,
            "badge": "🕉️ 100% Strict Jain Certified (Zero Root Veg / No Onion / No Garlic)" if is_safe else "🚨 STRICT JAIN NON-COMPLIANT",
            "explanation": "Free from all underground root vegetables (Kandmool), mushrooms, honey, and yeast." if is_safe else f"Contains {len(violations)} non-Jain ingredients."
        }

    @classmethod
    def evaluate_vrat(cls, text: str) -> Dict[str, Any]:
        """Evaluates Hindu Fasting (Navratri / Shivratri / Ekadashi Vrat) compliance."""
        t_low = text.lower()
        violations = []
        permitted_found = []

        # Check for regular grains
        for grain in cls.VRAT_FORBIDDEN_GRAINS:
            if grain == "atta":
                # Check for regular wheat atta, not sacred fasting flours like kuttu ka atta or singhara atta
                if re.search(r"(?<!kuttu ka )(?<!kuttu )(?<!singhara ka )(?<!singhara )(?<!rajgira ka )(?<!rajgira )\batta\b", t_low):
                    violations.append("Regular Grain / Pulse: 'Atta' (Wheat flour prohibited during Vrat)")
            elif re.search(rf"\b{grain}\b", t_low):
                violations.append(f"Regular Grain / Pulse: '{grain.title()}' (Grain consumption prohibited during Vrat)")

        # Check for table salt (must be Sendha Namak)
        if ("salt" in t_low or "sodium" in t_low) and "sendha" not in t_low and "rock salt" not in t_low:
            violations.append("Ordinary Table/Iodized Salt: Ordinary salt is processed and prohibited during sacred fasts; requires Sendha Namak (Rock Salt).")

        # Check for onion/garlic
        if re.search(r"\b(onion|garlic|pyaaz|lahsun)\b", t_low):
            violations.append("Onion / Garlic: Rajasic/Tamasic spice strictly forbidden during sacred fasts.")

        # Check for permitted fasting ingredients
        for p in cls.VRAT_PERMITTED:
            if p in t_low:
                permitted_found.append(p.title())

        is_safe = len(violations) == 0 and len(permitted_found) > 0
        return {
            "compliant": is_safe,
            "violations": violations,
            "permitted_found": list(set(permitted_found)),
            "badge": "🪔 100% Pure Vrat / Fasting Approved (Sendha Namak Only)" if is_safe else "⚠️ NOT VRAT COMPLIANT",
            "explanation": f"Crafted with sacred fasting flours/ingredients ({', '.join(permitted_found[:3])})." if is_safe else f"Violates {len(violations)} sacred fasting dietary rules."
        }

    @classmethod
    def evaluate_sattvic(cls, text: str) -> Dict[str, Any]:
        """Evaluates Ayurvedic Sattvic Diet (clarity, vitality, and digestive peace)."""
        t_low = text.lower()
        tamasic_terms = [
            "onion", "garlic", "mushroom", "vinegar", "caffeine", "coffee", "tea", "alcohol",
            "preservative", "sodium benzoate", "monosodium glutamate", "msg", "artificial flavor"
        ]
        found = [term.title() for term in tamasic_terms if re.search(rf"\b{term}\b", t_low)]
        is_sattvic = len(found) == 0
        return {
            "compliant": is_sattvic,
            "tamasic_ingredients": found,
            "badge": "🧘 Sattvic Prana Verified (Zero Onion, Garlic, or Synthetic Chemicals)" if is_sattvic else "⚠️ Contains Rajasic / Tamasic Ingredients",
            "explanation": "Promotes mental clarity, Ojas, and balanced digestive agni." if is_sattvic else f"Contains stimulants or heavy Tamasic items: {', '.join(found)}."
        }


class IndianAdulterationDetector:
    """
    Exposes prevalent misleading labelling practices in the Indian FMCG sector:
    - Palm Oil / Palmolein in namkeens, biscuits, and chocolates
    - Atta vs Maida masking (e.g. 70% Maida labelled as 'Whole Wheat')
    - Hidden liquid glucose, invert sugar, and maltodextrin syrups
    - Class II synthetic chemical preservatives (INS 211, INS 224)
    """

    PALM_OIL_TERMS = [
        "palm oil", "palmolein", "refined palmolein", "palm kernel oil", "fractionated palm oil",
        "hydrogenated vegetable oil", "hydrogenated vegetable fat", "vanaspati", "dalda",
        "edible vegetable fat (palm)", "edible vegetable oil (palm)"
    ]

    HIDDEN_SUGAR_SYRUPS = [
        "invert sugar syrup", "invert syrup", "liquid glucose", "glucose syrup",
        "maltodextrin", "malt extract", "corn syrup", "high fructose corn syrup",
        "caramel color", "caramel colour (ins 150d)", "dextrose monohydrate"
    ]

    CLASS_2_PRESERVATIVES = {
        "ins 211": "Sodium Benzoate (Synthetic Chemical Preservative)",
        "sodium benzoate": "Sodium Benzoate (Synthetic Chemical Preservative)",
        "ins 224": "Potassium Metabisulphite (Sulphur-based preservative)",
        "potassium metabisulphite": "Potassium Metabisulphite (Sulphur-based preservative)",
        "ins 220": "Sulphur Dioxide (Allergen / Asthmatic trigger)",
        "ins 202": "Potassium Sorbate (Anti-fungal preservative)",
        "ins 102": "Tartrazine (Synthetic Coal-Tar Yellow Dye - Linked to Hyperactivity)"
    }

    @classmethod
    def audit_adulterants(cls, product_name: str, ingredients_text: str) -> Dict[str, Any]:
        """Performs comprehensive Indian adulterant and masking audit."""
        t_low = ingredients_text.lower()
        name_low = product_name.lower()

        # 1. Palm Oil / Palmolein Detection
        palm_found = []
        for term in cls.PALM_OIL_TERMS:
            if term in t_low:
                palm_found.append(term.title())

        # 2. Atta vs Maida Masking Detector
        # Many Indian brands market "Atta Bread" or "Wheat Biscuits" but the 1st ingredient is Maida
        atta_claimed = any(w in name_low for w in ["atta", "whole wheat", "multigrain", "wheat"])
        maida_present = any(w in t_low for w in ["maida", "refined wheat flour", "enriched wheat flour"])
        maida_is_primary = False
        if maida_present:
            # Check if maida appears before whole wheat or in top 2 ingredients
            first_ingredients = t_low.split(",")[:2]
            for fi in first_ingredients:
                if any(w in fi for w in ["maida", "refined wheat flour"]):
                    maida_is_primary = True

        atta_masking_alert = None
        if atta_claimed and maida_is_primary:
            atta_masking_alert = {
                "detected": True,
                "message": "🌾 'Atta' Masking Detected: Front label claims Whole Wheat/Atta, but ingredient declaration reveals Refined Wheat Flour (Maida) as the predominant base!"
            }

        # 3. Hidden Sugar Syrups
        sugars_found = []
        for s in cls.HIDDEN_SUGAR_SYRUPS:
            if s in t_low:
                sugars_found.append(s.title())

        # 4. Class II Preservatives & Artificial Dyes
        preservatives_found = []
        for code, desc in cls.CLASS_2_PRESERVATIVES.items():
            if code in t_low:
                preservatives_found.append(desc)

        # Health score calculation (100 is pure clean label, down to 20 for heavily adulterated)
        penalty = 0
        if palm_found:
            penalty += 30
        if atta_masking_alert:
            penalty += 20
        if sugars_found:
            penalty += len(sugars_found) * 10
        if preservatives_found:
            penalty += len(preservatives_found) * 10

        purity_score = max(10, 100 - penalty)

        return {
            "purity_score": purity_score,
            "has_palm_oil": len(palm_found) > 0,
            "palm_oil_terms": palm_found,
            "atta_masking": atta_masking_alert,
            "hidden_sugars": sugars_found,
            "class_2_preservatives": preservatives_found,
            "clean_fat_swaps": ["Cold-Pressed Mustard Oil (Kacchi Ghani)", "Cold-Pressed Groundnut Oil", "Pure A2 Desi Cow Ghee"] if palm_found else []
        }


class AyurvedicEngine:
    """
    Evaluates Ayurvedic food compatibility (Viruddha Ahara - Incompatible Food Pairings)
    which disrupt digestive agni and create toxic endotoxins (Ama).
    """

    INCOMPATIBLE_COMBINATIONS = [
        {
            "pair": ["milk", "dairy", "dahi", "curd"],
            "conflict": ["citrus", "lemon", "lime", "orange", "sour", "citric acid", "tamarind", "amchur"],
            "name": "Ksheera & Amla Phala (Milk + Sour/Citrus)",
            "risk": "Milk proteins curdle in the presence of intense acids, impairing stomach agni, causing bloating and indigestion."
        },
        {
            "pair": ["milk", "dairy", "paneer"],
            "conflict": ["fish", "prawn", "seafood", "meat"],
            "name": "Matsya & Ksheera (Fish + Milk)",
            "risk": "Opposing cellular potencies (Virya): Milk is cooling/sweet while fish is heating. Incompatible digestion can trigger dermatological reactions and inflammatory Ama."
        },
        {
            "pair": ["honey"],
            "conflict": ["heated", "baked", "boiled", "hot water"],
            "name": "Ushna Madhu (Heated Honey)",
            "risk": "Charaka Samhita warns that heating honey past 40°C degrades enzymes into toxic, insoluble residues known as Amavisha."
        },
        {
            "pair": ["curd", "dahi", "yogurt"],
            "conflict": ["night", "dinner"],
            "name": "Ratri Dadhi (Curd Consumption at Night)",
            "risk": "Curd is heavy (Guru) and channel-blocking (Abhishyandi). Consumed late, it obstructs micro-circulatory channels and aggravates Kapha/mucus."
        }
    ]

    @classmethod
    def evaluate_viruddha_ahara(cls, ingredients_text: str) -> List[Dict[str, str]]:
        """Identifies incompatible food combinations in the product declaration."""
        t_low = ingredients_text.lower()
        detected = []

        for combo in cls.INCOMPATIBLE_COMBINATIONS:
            has_first = any(re.search(rf"\b{k}\b", t_low) for k in combo["pair"])
            has_second = any(re.search(rf"\b{c}\b", t_low) for c in combo["conflict"])
            if has_first and has_second:
                detected.append({
                    "name": combo["name"],
                    "risk": combo["risk"]
                })

        return detected


class MilletRecommendationEngine:
    """
    Shree Anna (Indian National Millet Mission) Superfood Recommendation Engine.
    Transforms high-GI Indian staples (white rice, refined atta) into ancient, low-GI superfoods.
    """

    MILLET_CATALOG = {
        "ragi": {
            "name": "Organic Sprouted Ragi (Finger Millet)",
            "benefits": "Contains 344mg Calcium/100g (30x more than rice!), rich in non-heme Iron. Low glycemic index stabilizes postprandial blood sugar.",
            "best_for": "Diabetes, Osteopenia, Bone Density, Anemia",
            "culinary_use": "Ragi Dosa, Ragi Mudde, Ragi Cookies, Porridge"
        },
        "jowar": {
            "name": "Whole Grain Jowar (Sorghum)",
            "benefits": "Certified Gluten-Free, packed with resistant starch and polyphenolic anthocyanins that protect vascular endothelium.",
            "best_for": "Celiac Disease, Cardiovascular Wellness, Hypertension",
            "culinary_use": "Jowar Bhakri/Roti, Jowar Puffs, Upma"
        },
        "bajra": {
            "name": "Pearl Millet (Bajra)",
            "benefits": "High Magnesium content relaxes cardiac muscles and smooth vessels. Rich in prebiotic fibers that optimize bowel transit.",
            "best_for": "Hypertension, Constipation, Cellular Metabolism",
            "culinary_use": "Bajra Roti, Bajra Khichdi"
        },
        "makhana": {
            "name": "Slow-Roasted Makhana (Foxnuts / Lotus Seeds)",
            "benefits": "Ultra-low sodium (<5mg), low Glycemic Index, 10g clean protein per 100g with anti-aging flavonoid kaempferol.",
            "best_for": "Hypertension, Diabetic Evening Snacking, Kidney Health",
            "culinary_use": "Evening snack roasted in A2 Ghee with Sendha Namak"
        },
        "sattu": {
            "name": "Pure Roasted Bengal Gram Sattu",
            "benefits": "Native Indian clean protein powerhouse (over 20g protein/100g) with zero chemical emulsifiers or whey isolates. Cooling Pitta pacifier.",
            "best_for": "Muscle Recovery, High Protein Vegan, GI Cooling",
            "culinary_use": "Sattu Sherbet, Sattu Paratha"
        }
    }

    @classmethod
    def get_swaps_for_query(cls, query: str, medical_history: str = "") -> List[Dict[str, Any]]:
        """Maps cravings or unhealthy foods to Shree Anna superfood alternatives."""
        q_low = query.lower()
        swaps = []

        if any(w in q_low for w in ["biscuit", "cookie", "cake", "sweet", "bread", "wheat"]):
            swaps.append(cls.MILLET_CATALOG["ragi"])
            swaps.append(cls.MILLET_CATALOG["jowar"])
        if any(w in q_low for w in ["snack", "chips", "namkeen", "crisp", "papad", "bhujia"]):
            swaps.append(cls.MILLET_CATALOG["makhana"])
        if any(w in q_low for w in ["protein", "shake", "powder", "bar", "gym"]):
            swaps.append(cls.MILLET_CATALOG["sattu"])
            swaps.append(cls.MILLET_CATALOG["ragi"])
        if any(w in q_low for w in ["roti", "flour", "atta", "rice", "noodle", "pasta"]):
            swaps.append(cls.MILLET_CATALOG["jowar"])
            swaps.append(cls.MILLET_CATALOG["bajra"])

        if not swaps:
            # Default top superfoods
            swaps = [cls.MILLET_CATALOG["makhana"], cls.MILLET_CATALOG["ragi"], cls.MILLET_CATALOG["sattu"]]

        return swaps
