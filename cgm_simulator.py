"""
SafeBite AI - Clinical CGM Simulator, NOVA Processing Scorer,
and Smart 1:1 Safe Food Swap Engine.
"""

import math
from typing import Dict, Any, List, Optional, Tuple
from schemas import NutritionFacts, Ingredients, Allergens


class CgmGlucosePredictor:
    """
    Simulates postprandial blood glucose trajectory over 180 minutes
    based on Net Carbohydrates, Glycemic Index (GI), Glycemic Load (GL),
    and physiological Fat/Protein Gastric Emptying Buffering.
    """

    @classmethod
    def simulate_glucose_curve(
        cls,
        nutrition: Optional[NutritionFacts],
        is_diabetic: bool = False,
        baseline_mg_dl: float = 95.0
    ) -> Dict[str, Any]:
        """
        Simulates 180-minute dynamic glucose trajectory:
        G(t) = G_baseline + Delta_G_max * (t / t_peak) * exp(1 - t / t_peak)
        """
        if not nutrition or nutrition.carbs_g is None:
            # Baseline curve when numerical carbs are unverified
            times = list(range(0, 185, 15))
            curve = [{"time_min": t, "glucose_mg_dl": round(baseline_mg_dl, 1)} for t in times]
            return {
                "available": False,
                "curve": curve,
                "peak_glucose": baseline_mg_dl,
                "delta_peak": 0.0,
                "time_to_peak_min": 45,
                "glycemic_load": 0.0,
                "risk_level": "UNKNOWN",
                "summary": "Nutrition facts unavailable for CGM blood glucose simulation.",
                "svg_chart": cls._generate_svg_chart(curve, baseline_mg_dl, baseline_mg_dl, "UNKNOWN")
            }

        carbs = nutrition.carbs_g or 0.0
        fiber = nutrition.fiber_g or 0.0
        sugar = nutrition.sugar_g or 0.0
        fat = nutrition.fat_g or 0.0
        protein = nutrition.protein_g or 0.0

        # Net Carbs = Total Carbs - Fiber
        net_carbs = max(0.0, carbs - fiber)

        # Estimate Glycemic Index (GI) from sugar-to-carb ratio & fiber
        if net_carbs > 0:
            sugar_ratio = min(1.0, sugar / net_carbs)
            estimated_gi = 45.0 + (sugar_ratio * 40.0) - min(25.0, fiber * 3.0)
            estimated_gi = max(25.0, min(95.0, estimated_gi))
        else:
            estimated_gi = 25.0

        # Glycemic Load: GL = (GI * Net Carbs) / 100
        gl = round((estimated_gi * net_carbs) / 100.0, 1)

        # Gastric Emptying Attenuation: Fat & Protein slow stomach emptying
        buffer_factor = 1.0 / (1.0 + (fat * 0.03) + (protein * 0.02) + (fiber * 0.04))

        # Peak delta: in diabetics, insulin resistance amplifies peak amplitude by ~1.6x
        diabetic_multiplier = 1.65 if is_diabetic else 1.0
        delta_max = (gl * 2.8 * buffer_factor) * diabetic_multiplier

        # Peak time: fat and fiber delay the spike time from 40 min to 60-75 min
        t_peak = 40.0 + min(35.0, (fat * 1.2) + (fiber * 1.5))

        # Generate trajectory points
        times = [0, 15, 30, 45, 60, 75, 90, 105, 120, 150, 180]
        curve = []
        for t in times:
            if t == 0:
                val = baseline_mg_dl
            else:
                x = t / t_peak
                # Standard pharmacokinetics absorption-elimination model
                curve_factor = x * math.exp(1.0 - x)
                val = baseline_mg_dl + (delta_max * curve_factor)
            curve.append({"time_min": t, "glucose_mg_dl": round(val, 1)})

        peak_val = round(baseline_mg_dl + delta_max, 1)
        velocity = round(delta_max / t_peak, 2)  # mg/dL per min

        if delta_max >= 55.0:
            risk = "DANGEROUS_SPIKE"
            summary = f"🚨 SEVERE GLYCEMIC SPIKE: Estimated peak {peak_val:.0f} mg/dL (+{delta_max:.0f} mg/dL surge). Rapid glucose velocity {velocity} mg/dL/min."
        elif delta_max >= 30.0:
            risk = "MODERATE_SPIKE"
            summary = f"⚠️ MODERATE RISE: Peak {peak_val:.0f} mg/dL (+{delta_max:.0f} mg/dL). Satiety buffer moderately delayed by fat/protein."
        else:
            risk = "STABLE_GLYCEMIC"
            summary = f"✅ STABLE GLYCEMIC RESPONSE: Peak {peak_val:.0f} mg/dL (+{delta_max:.0f} mg/dL). Minimal insulin demand."

        svg_chart = cls._generate_svg_chart(curve, baseline_mg_dl, peak_val, risk)

        return {
            "available": True,
            "curve": curve,
            "peak_glucose": peak_val,
            "delta_peak": round(delta_max, 1),
            "time_to_peak_min": round(t_peak),
            "net_carbs_g": round(net_carbs, 1),
            "estimated_gi": round(estimated_gi),
            "glycemic_load": gl,
            "glucose_velocity": velocity,
            "risk_level": risk,
            "summary": summary,
            "svg_chart": svg_chart
        }

    @classmethod
    def _generate_svg_chart(
        cls,
        curve: List[Dict[str, Any]],
        baseline: float,
        peak: float,
        risk: str
    ) -> str:
        """Generates a responsive standalone SVG visualization of the CGM trajectory."""
        width = 540
        height = 180
        padding_x = 45
        padding_y = 25

        color_map = {
            "DANGEROUS_SPIKE": "#DC2626",
            "MODERATE_SPIKE": "#F59E0B",
            "STABLE_GLYCEMIC": "#10B981",
            "UNKNOWN": "#64748B"
        }
        line_color = color_map.get(risk, "#10B981")

        max_y = max(160.0, peak + 15.0)
        min_y = max(60.0, baseline - 15.0)
        y_range = max_y - min_y

        def scale_x(t: float) -> float:
            return padding_x + (t / 180.0) * (width - 2 * padding_x)

        def scale_y(g: float) -> float:
            return (height - padding_y) - ((g - min_y) / y_range) * (height - 2 * padding_y)

        # Build path coordinates
        points = []
        for pt in curve:
            px = scale_x(pt["time_min"])
            py = scale_y(pt["glucose_mg_dl"])
            points.append(f"{px:.1f},{py:.1f}")
        path_data = "M " + " L ".join(points)

        # Baseline dashed line
        baseline_y = scale_y(baseline)
        target_upper_y = scale_y(140.0)

        svg = f"""
        <svg viewBox="0 0 {width} {height}" style="width:100%; max-width:{width}px; background:#0F172A; border-radius:10px; font-family:sans-serif; box-shadow:0 2px 8px rgba(0,0,0,0.15);">
            <!-- Target In-Range Safe Zone (70 - 140 mg/dL) -->
            <rect x="{padding_x}" y="{target_upper_y}" width="{width - 2*padding_x}" height="{baseline_y - target_upper_y}" fill="rgba(16, 185, 129, 0.08)" />
            <text x="{width - padding_x - 5}" y="{target_upper_y - 4}" fill="#6EE7B7" font-size="9" text-anchor="end">Safe Target (&lt;140 mg/dL)</text>
            
            <!-- Baseline Grid Line -->
            <line x1="{padding_x}" y1="{baseline_y}" x2="{width - padding_x}" y2="{baseline_y}" stroke="#334155" stroke-dasharray="4,4" stroke-width="1" />
            <text x="{padding_x - 6}" y="{baseline_y + 3}" fill="#94A3B8" font-size="9" text-anchor="end">{baseline:.0f}</text>

            <!-- Peak Annotation -->
            <text x="{width - padding_x - 5}" y="20" fill="{line_color}" font-weight="bold" font-size="11" text-anchor="end">Peak: {peak:.0f} mg/dL</text>

            <!-- Trajectory Path -->
            <path d="{path_data}" fill="none" stroke="{line_color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
            
            <!-- Time Axis Labels -->
            <text x="{scale_x(0)}" y="{height - 8}" fill="#64748B" font-size="9" text-anchor="middle">0m</text>
            <text x="{scale_x(60)}" y="{height - 8}" fill="#64748B" font-size="9" text-anchor="middle">60m</text>
            <text x="{scale_x(120)}" y="{height - 8}" fill="#64748B" font-size="9" text-anchor="middle">120m</text>
            <text x="{scale_x(180)}" y="{height - 8}" fill="#64748B" font-size="9" text-anchor="middle">180m</text>
        </svg>
        """
        return svg


class NovaProcessingScorer:
    """
    Evaluates food ultra-processing according to the peer-reviewed scientific
    NOVA Food Classification System (University of São Paulo / WHO / FAO):
    - NOVA 1: Unprocessed / Minimally processed foods
    - NOVA 2: Processed culinary ingredients
    - NOVA 3: Processed foods
    - NOVA 4: Ultra-processed food formulations (UPF)
    """

    NOVA_4_MARKERS = [
        # Emulsifiers & stabilizers that erode gut mucus
        "polysorbate", "carboxymethylcellulose", "carrageenan", "soy lecithin", "sunflower lecithin",
        "mono- and diglycerides", "e471", "e466", "e407", "maltodextrin",
        # Industrial sweeteners
        "high fructose corn syrup", "sucralose", "aspartame", "acesulfame potassium", "acesulfame k",
        "saccharin", "sorbitol", "maltitol syrup", "invert sugar syrup", "liquid glucose",
        # Hydrogenated fats & synthetic flavor/color
        "hydrogenated vegetable oil", "vanaspati", "dalda", "fractionated palm oil",
        "monosodium glutamate", "msg", "disodium inosinate", "disodium guanylate",
        "caramel color", "tartrazine", "allura red", "sunset yellow", "synthetic flavor"
    ]

    @classmethod
    def evaluate_nova(cls, product_name: str, ingredients_text: str, additives_count: int = 0) -> Dict[str, Any]:
        """Assigns authoritative NOVA group and Clean Label Toxicity Score (0 - 100)."""
        t_low = ingredients_text.lower()
        upf_detected = []

        for marker in cls.NOVA_4_MARKERS:
            if marker in t_low:
                upf_detected.append(marker.title())

        # Determine NOVA group
        if len(upf_detected) >= 2 or additives_count >= 3:
            nova_group = 4
            nova_title = "NOVA 4 · Ultra-Processed Food (UPF)"
            nova_badge = "🚨 NOVA 4: Ultra-Processed Formulation"
            nova_desc = "Formulated from industrial substances with chemical emulsifiers, artificial flavors, and refined extracts not used in home culinary preparations."
            nova_color = "#DC2626"
            toxicity_score = max(15, 100 - (len(upf_detected) * 18 + additives_count * 10))
        elif len(upf_detected) == 1 or additives_count >= 1:
            nova_group = 3
            nova_title = "NOVA 3 · Processed Food"
            nova_badge = "⚠️ NOVA 3: Processed Food"
            nova_desc = "Created by adding culinary ingredients (salt, oil, sugar) with minor industrial preservation agents to whole foods."
            nova_color = "#F59E0B"
            toxicity_score = max(40, 85 - (len(upf_detected) * 15 + additives_count * 8))
        elif any(w in t_low for w in ["oil", "butter", "salt", "sugar", "ghee"]) and len(t_low.split(",")) <= 3:
            nova_group = 2
            nova_title = "NOVA 2 · Processed Culinary Ingredient"
            nova_badge = "🟡 NOVA 2: Culinary Ingredient"
            nova_desc = "Substance extracted from nature used in kitchens to season and cook whole foods (e.g. cold-pressed oils, butter, sea salt)."
            nova_color = "#3B82F6"
            toxicity_score = 90
        else:
            nova_group = 1
            nova_title = "NOVA 1 · Unprocessed or Minimally Processed"
            nova_badge = "🌱 NOVA 1: Whole Food / Minimally Processed"
            nova_desc = "Natural edible parts of plants or animals subjected only to cleaning, drying, boiling, or non-chemical fermentation."
            nova_color = "#10B981"
            toxicity_score = 98

        return {
            "nova_group": nova_group,
            "nova_title": nova_title,
            "nova_badge": nova_badge,
            "nova_desc": nova_desc,
            "nova_color": nova_color,
            "clean_label_score": toxicity_score,
            "upf_markers_found": upf_detected
        }


class ClinicalRadarMatrix:
    """
    Computes a 6-axis clinical nutritional rating matrix:
    1. Glycemic Stability
    2. Cardiovascular Safety
    3. Gut Microbiome Health
    4. Protein Purity
    5. Clean Label Integrity
    6. Satiety Index
    """

    @classmethod
    def compute_radar_scores(
        cls,
        nutrition: Optional[NutritionFacts],
        ingredients: Optional[Ingredients],
        allergens: Optional[Allergens]
    ) -> Dict[str, float]:
        """Calculates normalized 0-100 scores across 6 clinical axes."""
        # 1. Glycemic Stability (Low sugar, high fiber)
        if nutrition and nutrition.sugar_g is not None and nutrition.carbs_g is not None:
            sugar = nutrition.sugar_g
            fiber = nutrition.fiber_g or 0.0
            glycemic = max(10.0, min(100.0, 100.0 - (sugar * 3.5) + (fiber * 5.0)))
        else:
            glycemic = 70.0

        # 2. Cardiovascular Safety (Low sodium, low sat fat)
        if nutrition and nutrition.sodium_mg is not None:
            sod = nutrition.sodium_mg
            sat_fat = nutrition.saturated_fat_g or 0.0
            cardio = max(10.0, min(100.0, 100.0 - (sod / 12.0) - (sat_fat * 6.0)))
        else:
            cardio = 75.0

        # 3. Gut Microbiome Health (High fiber, absence of emulsifiers)
        gut = 80.0
        if ingredients and ingredients.additives:
            gut -= len(ingredients.additives) * 8.0
        if nutrition and nutrition.fiber_g:
            gut += nutrition.fiber_g * 4.0
        gut = max(15.0, min(100.0, gut))

        # 4. Protein Purity (Protein ratio)
        if nutrition and nutrition.protein_g is not None and nutrition.calories:
            protein_cal = nutrition.protein_g * 4.0
            p_ratio = protein_cal / max(1.0, nutrition.calories)
            protein_score = min(100.0, max(20.0, p_ratio * 300.0))
        else:
            protein_score = 65.0

        # 5. Clean Label Integrity (Clean label, zero synthetic chemicals)
        if ingredients and ingredients.is_clean_label:
            clean = 95.0
        elif ingredients and ingredients.additives:
            clean = max(20.0, 90.0 - len(ingredients.additives) * 12.0)
        else:
            clean = 70.0

        # 6. Satiety Index (High protein + high fiber / low energy density)
        sat = 50.0
        if nutrition:
            sat += (nutrition.protein_g or 0.0) * 2.5 + (nutrition.fiber_g or 0.0) * 4.0 - ((nutrition.sugar_g or 0.0) * 1.5)
        sat = max(20.0, min(100.0, sat))

        return {
            "Glycemic Stability": round(glycemic, 1),
            "Cardiovascular Safety": round(cardio, 1),
            "Gut Microbiome": round(gut, 1),
            "Protein Purity": round(protein_score, 1),
            "Clean Label": round(clean, 1),
            "Satiety Index": round(sat, 1)
        }


class SmartSafeSwapEngine:
    """
    1-Click Smart Safe Alternative Recommender.
    Whenever a product is flagged with warnings (High Sugar, Palm Oil, Allergens, or UPF),
    generates 3 identical 1:1 clean-label replacements with delta percentage comparisons.
    """

    SWAP_REGISTRY = {
        "chocolate": [
            {
                "swap_name": "Amul 99% Single-Origin Bitter Dark Chocolate",
                "brand": "Amul Pure Cacao",
                "delta_sugar": "-98% Sugar",
                "delta_fiber": "+320% Fiber",
                "clean_perks": "Zero Palm Oil · 100% Cocoa Butter · Diabetic Safe",
                "buy_query": "amul 99 percent dark chocolate"
            },
            {
                "swap_name": "Pascati 85% Organic Cacao Bar (Sea Salt)",
                "brand": "Pascati Artisanal",
                "delta_sugar": "-82% Sugar",
                "delta_fiber": "+210% Fiber",
                "clean_perks": "Fair-Trade Organic · Certified Vegan · No Emulsifiers",
                "buy_query": "pascati 85 dark chocolate"
            }
        ],
        "cookie": [
            {
                "swap_name": "100% Clean Double Cocoa Protein Cookie",
                "brand": "The Whole Truth",
                "delta_sugar": "-75% Refined Sugar",
                "delta_fiber": "+400% Fiber",
                "clean_perks": "Sweetened with Dates Only · Zero Maida · Zero Palm Oil",
                "buy_query": "the whole truth double cocoa protein cookie"
            },
            {
                "swap_name": "Sprouted Ragi & Almond Crunchy Biscuits",
                "brand": "Early Foods Organic",
                "delta_sugar": "-85% Added Sugar",
                "delta_fiber": "+280% Fiber",
                "clean_perks": "Ancient Millets (Shree Anna) · High Bioavailable Calcium",
                "buy_query": "early foods sprouted ragi cookies"
            }
        ],
        "snack": [
            {
                "swap_name": "Slow-Roasted Makhana with Pink Himalayan Salt",
                "brand": "Farmley Pure",
                "delta_sugar": "0g Added Sugar",
                "delta_fiber": "+220% Fiber",
                "clean_perks": "Low Sodium · Zero Palm Olein · Native Foxnut Protein",
                "buy_query": "farmley roasted makhana himalayan salt"
            },
            {
                "swap_name": "Vacuum-Cooked Golden Sweet Potato Crisps",
                "brand": "To Be Honest (TBH)",
                "delta_sugar": "No Refined Sugar",
                "delta_fiber": "+180% Fiber",
                "clean_perks": "Cold-Pressed Rice Bran Oil · 50% Less Oil than Namkeen",
                "buy_query": "to be honest sweet potato chips"
            }
        ],
        "bread": [
            {
                "swap_name": "100% Whole Wheat Country Sourdough Loaf",
                "brand": "The Baker's Dozen",
                "delta_sugar": "0g Added Sugar",
                "delta_fiber": "+160% Fiber",
                "clean_perks": "24-hr Wild Sourdough Fermentation · Zero Bread Improvers · Zero Maida",
                "buy_query": "the bakers dozen sourdough bread"
            }
        ],
        "pasta": [
            {
                "swap_name": "100% Chickpea High-Protein Rotini Pasta",
                "brand": "Slurrp Farm Pure",
                "delta_sugar": "0g Added Sugar",
                "delta_fiber": "+350% Fiber",
                "clean_perks": "Gluten-Free · Single Ingredient Legume Base · 24g Plant Protein",
                "buy_query": "chickpea rotini pasta"
            }
        ]
    }

    @classmethod
    def get_smart_swaps(cls, product_name: str, category: str = "") -> List[Dict[str, Any]]:
        """Returns 2-3 optimal clean swaps tailored to product type."""
        combined = f"{product_name} {category}".lower()

        for key, swaps in cls.SWAP_REGISTRY.items():
            if key in combined:
                return swaps

        # Default smart healthy swaps
        return cls.SWAP_REGISTRY["snack"]
