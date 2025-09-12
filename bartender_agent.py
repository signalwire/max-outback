#!/usr/bin/env python3
"""
Bartender AI Agent - An AI-powered bartender for drink ordering
Based on the Holy Guacamole architecture
"""

import os
import sys
import json
import random
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

# SignalWire imports
from signalwire_agents import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult

# Optional imports for advanced features
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("Warning: scikit-learn not installed. Fuzzy drink matching disabled.")

# Try to load dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Using environment variables only.")

def dollars_to_words(amount):
    """Convert dollar amount to spoken English"""
    # Handle zero
    if amount == 0:
        return "zero dollars"
    
    # Split into dollars and cents
    dollars = int(amount)
    cents = round((amount - dollars) * 100)
    
    # Number words
    ones = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
    teens = ["ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", 
            "sixteen", "seventeen", "eighteen", "nineteen"]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
    
    def number_to_words(n):
        """Convert number under 1000 to words"""
        if n == 0:
            return ""
        elif n < 10:
            return ones[n]
        elif n < 20:
            return teens[n-10]
        elif n < 100:
            return tens[n//10] + ("-" + ones[n%10] if n%10 > 0 else "")
        else:
            hundred_part = ones[n//100] + " hundred"
            remainder = n % 100
            if remainder == 0:
                return hundred_part
            elif remainder < 10:
                return hundred_part + " and " + ones[remainder]
            elif remainder < 20:
                return hundred_part + " and " + teens[remainder-10]
            else:
                return hundred_part + " and " + tens[remainder//10] + ("-" + ones[remainder%10] if remainder%10 > 0 else "")
    
    # Build the result
    result = []
    
    # Handle thousands
    if dollars >= 1000:
        thousands = dollars // 1000
        result.append(number_to_words(thousands) + " thousand")
        dollars = dollars % 1000
    
    # Handle hundreds and below
    if dollars > 0:
        result.append(number_to_words(dollars))
    
    # Add "dollar(s)"
    if result:
        dollar_amount = " ".join(result)
        if dollar_amount == "one":
            result = ["one dollar"]
        else:
            result = [" ".join(result) + " dollars"]
    else:
        result = []
    
    # Handle cents
    if cents > 0:
        if cents == 1:
            cent_str = "one cent"
        else:
            cent_str = number_to_words(cents) + " cents"
        
        if result:
            result.append("and " + cent_str)
        else:
            result = [cent_str]
    
    return " ".join(result) if result else "zero dollars"

# Drink Menu Database
DRINKS = {
    "cocktails": {
        "C001": {"name": "Margarita", "price": 10.00, "description": "Tequila, lime juice, triple sec, salt rim", "abv": 15, "category": "classic"},
        "C002": {"name": "Old Fashioned", "price": 12.00, "description": "Bourbon, bitters, sugar cube, orange peel", "abv": 35, "category": "classic"},
        "C003": {"name": "Mojito", "price": 11.00, "description": "White rum, mint, lime, sugar, soda water", "abv": 10, "category": "refreshing"},
        "C004": {"name": "Martini", "price": 13.00, "description": "Gin or vodka, dry vermouth, olive or lemon twist", "abv": 30, "category": "classic"},
        "C005": {"name": "Cosmopolitan", "price": 11.00, "description": "Vodka, cranberry, lime juice, triple sec", "abv": 20, "category": "classic"},
        "C006": {"name": "Manhattan", "price": 12.00, "description": "Rye whiskey, sweet vermouth, bitters, cherry", "abv": 30, "category": "classic"},
        "C007": {"name": "Negroni", "price": 11.00, "description": "Gin, Campari, sweet vermouth", "abv": 25, "category": "bitter"},
        "C008": {"name": "Moscow Mule", "price": 10.00, "description": "Vodka, ginger beer, lime, copper mug", "abv": 12, "category": "refreshing"},
        "C009": {"name": "Whiskey Sour", "price": 10.00, "description": "Bourbon, lemon juice, simple syrup, egg white", "abv": 20, "category": "sour"},
        "C010": {"name": "Mai Tai", "price": 12.00, "description": "Rum blend, orange liqueur, orgeat, lime", "abv": 25, "category": "tropical"}
    },
    "beer": {
        "B001": {"name": "IPA", "price": 7.00, "description": "Hoppy, bitter, citrus notes - 6.5% ABV", "abv": 6.5, "category": "draft"},
        "B002": {"name": "Lager", "price": 6.00, "description": "Light, crisp, refreshing - 5% ABV", "abv": 5.0, "category": "draft"},
        "B003": {"name": "Stout", "price": 8.00, "description": "Dark, rich, coffee notes - 7% ABV", "abv": 7.0, "category": "draft"},
        "B004": {"name": "Wheat Beer", "price": 6.50, "description": "Smooth, citrusy, cloudy - 5.5% ABV", "abv": 5.5, "category": "draft"},
        "B005": {"name": "Pale Ale", "price": 7.00, "description": "Balanced, hoppy, golden - 5.8% ABV", "abv": 5.8, "category": "draft"}
    },
    "wine": {
        "W001": {"name": "House Red", "price": 9.00, "description": "Cabernet Sauvignon - Full bodied", "abv": 13, "category": "red"},
        "W002": {"name": "House White", "price": 9.00, "description": "Chardonnay - Crisp and buttery", "abv": 12, "category": "white"},
        "W003": {"name": "Prosecco", "price": 10.00, "description": "Italian sparkling - Light and bubbly", "abv": 11, "category": "sparkling"},
        "W004": {"name": "Pinot Noir", "price": 11.00, "description": "Light red - Earthy and smooth", "abv": 13, "category": "red"},
        "W005": {"name": "Sauvignon Blanc", "price": 10.00, "description": "Crisp white - Citrus and herbs", "abv": 12, "category": "white"}
    },
    "non_alcoholic": {
        "N001": {"name": "Virgin Mojito", "price": 6.00, "description": "Mint, lime, sugar, soda water", "abv": 0, "category": "mocktail"},
        "N002": {"name": "Shirley Temple", "price": 5.00, "description": "Ginger ale, grenadine, maraschino cherry", "abv": 0, "category": "mocktail"},
        "N003": {"name": "Virgin Mary", "price": 6.00, "description": "Tomato juice, worcestershire, tabasco, celery", "abv": 0, "category": "mocktail"},
        "N004": {"name": "Soda", "price": 3.00, "description": "Coke, Sprite, Ginger Ale, Tonic", "abv": 0, "category": "soft"},
        "N005": {"name": "Juice", "price": 4.00, "description": "Orange, cranberry, pineapple, grapefruit", "abv": 0, "category": "soft"},
        "N006": {"name": "Water", "price": 0.00, "description": "Still or sparkling", "abv": 0, "category": "water"}
    }
}

# Service limits
MAX_DRINKS_PER_TAB = 20
MAX_TAB_AMOUNT = 200.00

# Drink aliases for better matching
DRINK_ALIASES = {
    "C001": ["marg", "margarita", "tequila drink"],
    "C002": ["old fashion", "bourbon drink", "whiskey cocktail"],
    "C003": ["mojito", "rum mint", "minty drink"],
    "C004": ["martini", "gin martini", "vodka martini", "dry martini"],
    "C005": ["cosmo", "cosmopolitan", "pink drink"],
    "B001": ["ipa", "india pale ale", "hoppy beer"],
    "B002": ["lager", "light beer", "regular beer"],
    "W001": ["red wine", "cab", "cabernet"],
    "W002": ["white wine", "chard", "chardonnay"],
    "N004": ["coke", "cola", "pepsi", "sprite", "7up", "ginger ale", "tonic", "tonic water", "soda water", "club soda"],
    "N005": ["juice", "orange juice", "oj", "cranberry juice", "cran", "pineapple juice", "grapefruit juice", "apple juice", "tomato juice"],
    "N006": ["water", "h2o", "aqua", "ice water", "tap water", "bottled water", "still water", "sparkling water"]
}

class BartenderAgent(AgentBase):
    """AI Bartender Agent for taking drink orders"""
    
    def __init__(self):
        super().__init__(
            name="Max"
        )
        
        # Initialize app attribute
        self._app = None
        self.route = "/swml"  # Default SWML route
        self.host = "0.0.0.0"  # Default host
        self.port = 3030  # Default port
        
        # Initialize TF-IDF for drink matching if available
        self.vectorizer = None
        self.drink_vectors = None
        self.sku_map = []
        
        if HAS_SKLEARN:
            self._initialize_tfidf()
        
        # Set personality and context
        self.prompt_add_section(
            "Personality",
            "You are Max, the friendly and professional bartender at Outback Bar. You're warm and welcoming, but always responsible. "
            "You should be casual and conversational, using phrases a real bartender would use. "
            "Add personality to your responses - you can be a bit witty and charming, but always professional. "
            "Remember to be concise and natural in your speech."
        )
        
        self.prompt_add_section(
            "Function Usage",
            "IMPORTANT: You don't have a memorized menu. Instead, you have access to functions that handle all drink operations:\n"
            "- When a customer orders ANY drink, immediately use the add_drink function\n"
            "- The function will validate if we have it and handle pricing automatically\n"
            "- If the drink doesn't exist, the function will tell you and you can suggest alternatives\n\n"
            "CLOSING TABS: This is a quick-service bar, not a long sit-down experience:\n"
            "- Most customers order 1-3 drinks and close immediately\n"
            "- Listen for completion signals: 'that's all', 'that's it', 'I'm done', 'nothing else'\n"
            "- After 2-3 drinks, ask 'Will that be all for you?'\n"
            "- When they indicate they're done, immediately say something like 'Perfect! Your total is $X. Ready to close out?'\n"
            "- Don't keep tabs open indefinitely - guide them to close promptly\n\n"
            "Example flows:\n"
            "Customer: 'I'll have a margarita and that's it'\n"
            "You: Use add_drink, then immediately offer to close: 'Great! That's $11.50. Ready to close out?'\n\n"
            "Customer: 'Two beers please'\n"
            "You: Add the beers, then ask: 'Anything else, or shall I close your tab?'"
        )
        
        # Define conversation contexts
        contexts = self.define_contexts()
        
        default_context = contexts.add_context("default") \
            .add_section("Goal", "Take drink orders efficiently while providing excellent service and practicing responsible alcohol service.")
        
        # GREETING STATE
        default_context.add_step("greeting") \
            .add_section("Current Task", "Welcome the customer and take their first order") \
            .add_bullets("Process", [
                "Welcome them warmly to Outback Bar",
                "Ask what they'd like to drink",
                "Current time: ${global_data.current_time}",
                "If it's 4-7 PM, mention happy hour discount on cocktails",
                "When they order ANYTHING, immediately use add_drink function",
                "Let the function handle validation and pricing"
            ]) \
            .set_step_criteria("Customer has ordered their first drink") \
            .set_functions(["add_drink", "check_happy_hour"]) \
            .set_valid_steps(["taking_order"])
        
        # TAKING ORDER STATE
        default_context.add_step("taking_order") \
            .add_section("Current Task", "Take orders and guide toward closing") \
            .add_bullets("Process", [
                "Current time: ${global_data.current_time}",
                "Current tab has ${global_data.tab_state.item_count} items",
                "Current total: $${global_data.tab_state.total}",
                "ALWAYS use add_drink function when customer orders",
                "After each drink, assess if they're done:",
                "  - 1-2 drinks: 'Anything else?'",
                "  - 3+ drinks: 'Will that be all for you?'",
                "Listen for completion phrases: 'that's all', 'that's it', 'I'm done'",
                "When they indicate completion, transition to closing_tab state",
                "Don't let tabs linger - this is quick service",
                "If they seem done, say: 'Ready to see your total?' and move to closing_tab"
            ]) \
            .set_step_criteria("Customer is ordering OR has indicated they're done") \
            .set_functions(["add_drink", "remove_drink", "review_tab", "check_happy_hour"]) \
            .set_valid_steps(["closing_tab"])
        
        # CLOSING TAB STATE
        default_context.add_step("closing_tab") \
            .add_section("Current Task", "Show total with tip options, then process payment") \
            .add_bullets("Process", [
                "IMMEDIATELY use review_tab with closing=true to show tip options",
                "Do NOT use close_tab until AFTER review_tab shows tip options",
                "Backend will calculate and present tip suggestions (18%, 20%, 25%)",
                "Wait for customer to choose a tip amount",
                "Only after customer selects tip, use close_tab with that percentage",
                "Keep it brief and efficient"
            ]) \
            .set_step_criteria("Customer has agreed to close or requested the check") \
            .set_functions(["close_tab", "review_tab"]) \
            .set_valid_steps(["tab_closed"])
        
        # TAB CLOSED STATE
        default_context.add_step("tab_closed") \
            .add_section("Current Task", "Thank the customer and prepare for next customer") \
            .add_bullets("Process", [
                "Thank them for their business",
                "Wish them a good day/evening",
                "Reset for next customer"
            ]) \
            .set_step_criteria("Tab has been closed and paid") \
            .set_functions([]) \
            .set_valid_steps(["greeting"])
        
        # Define SWAIG functions
        self._define_functions()
        
        # Configure voice
        self.add_language(
            name="English",
            code="en-US",
            voice="elevenlabs.charlie"
        )
        
        # Add speech hints
        self.add_hints([
            "margarita", "old fashioned", "mojito", "martini", "cosmopolitan",
            "manhattan", "negroni", "moscow mule", "whiskey sour", "mai tai",
            "beer", "ipa", "lager", "stout", "pale ale", "wheat beer",
            "wine", "red", "white", "prosecco", "pinot noir", "sauvignon blanc",
            "vodka", "gin", "rum", "whiskey", "tequila", "bourbon",
            "double", "rocks", "neat", "tall", "dirty", "dry",
            "tab", "check", "close out", "pay", "tip",
            "water", "soda", "juice", "virgin", "mocktail",
            "that's all", "that's it", "I'm done", "nothing else", "I'm good"
        ])
        
        # Initialize global data
        self.set_global_data({
            "bar_name": "Outback Bar",
            "current_time": datetime.now().strftime("%I:%M %p"),
            "current_hour": datetime.now().hour
        })
    
    def _initialize_tfidf(self):
        """Initialize TF-IDF vectorizer for drink matching"""
        corpus = []
        self.sku_map = []
        
        for category, items in DRINKS.items():
            for sku, item in items.items():
                text_parts = [item['name'], item['description']]
                
                if sku in DRINK_ALIASES:
                    text_parts.extend(DRINK_ALIASES[sku])
                
                text_parts.append(category)
                corpus.append(' '.join(text_parts).lower())
                self.sku_map.append((sku, item, category))
        
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words=None,
            max_features=200,
            sublinear_tf=True
        )
        self.drink_vectors = self.vectorizer.fit_transform(corpus)
    
    def _define_functions(self):
        """Define all SWAIG functions for bartender operations"""
        
        def get_tab_state(raw_data):
            """Get or initialize tab state"""
            global_data = raw_data.get("global_data", {})
            
            # Always update current time
            global_data["current_time"] = datetime.now().strftime("%I:%M %p")
            global_data["current_hour"] = datetime.now().hour
            
            if "tab_state" not in global_data:
                global_data["tab_state"] = {
                    "items": [],
                    "subtotal": 0.00,
                    "tax": 0.00,
                    "total": 0.00,
                    "item_count": 0,
                    "alcoholic_drinks": 0,
                    "last_drink_time": None
                }
            
            return global_data["tab_state"], global_data
        
        def save_tab_state(result, tab_state, global_data):
            """Save tab state to global data"""
            global_data["tab_state"] = tab_state
            result.update_global_data(global_data)
        
        def calculate_totals(items):
            """Calculate subtotal, tax, and total"""
            # Prices already include happy hour discount if applicable
            subtotal = round(sum(item["total"] for item in items), 2)
            tax = round(subtotal * 0.0875, 2)  # 8.75% tax
            total = round(subtotal + tax, 2)
            
            return subtotal, tax, total
        
        def check_responsible_service(tab_state):
            """Check if we should limit service"""
            if tab_state["alcoholic_drinks"] >= 5:
                return False, "I think that's enough for tonight. How about some water?"
            if tab_state["alcoholic_drinks"] >= 3:
                return True, "I'd recommend having some water with that."
            return True, None
        
        def find_drink(drink_name):
            """Find drink in menu by name with fuzzy matching"""
            drink_lower = drink_name.lower().strip()
            
            # Check exact matches
            for category, items in DRINKS.items():
                for sku, item_data in items.items():
                    if drink_lower == item_data["name"].lower():
                        return sku, item_data, category
            
            # Check aliases
            for sku, aliases in DRINK_ALIASES.items():
                if drink_lower in [alias.lower() for alias in aliases]:
                    for category, items in DRINKS.items():
                        if sku in items:
                            return sku, items[sku], category
            
            # TF-IDF matching if available
            if HAS_SKLEARN and self.vectorizer and self.drink_vectors is not None:
                try:
                    user_vector = self.vectorizer.transform([drink_lower])
                    similarities = cosine_similarity(user_vector, self.drink_vectors)[0]
                    best_idx = np.argmax(similarities)
                    best_score = similarities[best_idx]
                    
                    if best_score > 0.35:
                        sku, item_data, category = self.sku_map[best_idx]
                        return sku, item_data, category
                except:
                    pass
            
            return None, None, None
        
        @self.tool(
            name="add_drink",
            wait_file="/pouring.mp3",
            description="Add a drink to the customer's tab",
            parameters={
                "type": "object",
                "properties": {
                    "drink_name": {
                        "type": "string",
                        "description": "Name of the drink"
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "How many drinks",
                        "minimum": 1,
                        "maximum": 4
                    },
                    "modifications": {
                        "type": "string",
                        "description": "Optional: double, tall, rocks, neat, dirty, dry"
                    }
                },
                "required": ["drink_name"]
            }
        )
        def add_drink(args, raw_data):
            """Add drink to tab"""
            tab_state, global_data = get_tab_state(raw_data)
            drink_name = args["drink_name"]
            quantity = args.get("quantity", 1)
            modifications = args.get("modifications", "")
            
            # Find the drink
            sku, drink_data, category = find_drink(drink_name)
            
            if not sku:
                return SwaigFunctionResult(f"Sorry, we don't have '{drink_name}' on our menu. We have cocktails, beer, wine, and non-alcoholic options. What type of drink would you prefer?")
            
            # Check drink count limit
            current_count = sum(item["quantity"] for item in tab_state["items"])
            if current_count + quantity > MAX_DRINKS_PER_TAB:
                remaining = MAX_DRINKS_PER_TAB - current_count
                if remaining > 0:
                    return SwaigFunctionResult(f"You can only add {remaining} more drinks. We have a {MAX_DRINKS_PER_TAB} drink maximum per tab. Ready to close out?")
                else:
                    return SwaigFunctionResult(f"You've reached our {MAX_DRINKS_PER_TAB} drink limit. Your total is {dollars_to_words(tab_state['total'])}. Ready to close your tab?")
            
            # Check responsible service
            if drink_data["abv"] > 0:
                can_serve, message = check_responsible_service(tab_state)
                if not can_serve:
                    return SwaigFunctionResult(message)
            
            # Calculate price with modifications
            price = drink_data["price"]
            if "double" in modifications.lower():
                price += 3.00
            
            # Apply happy hour discount to display price
            display_price = price
            current_hour = datetime.now().hour
            is_happy_hour = 16 <= current_hour < 19 and category == "cocktails"
            if is_happy_hour:
                display_price = round(price * 0.8, 2)  # 20% off
            
            # Check tab total limit
            new_drink_total = display_price * quantity
            projected_subtotal = tab_state["subtotal"] + new_drink_total
            projected_tax = round(projected_subtotal * 0.0875, 2)
            projected_total = projected_subtotal + projected_tax
            
            if projected_total > MAX_TAB_AMOUNT:
                return SwaigFunctionResult(f"Adding this would put your tab over our {dollars_to_words(MAX_TAB_AMOUNT)} limit. Your current total is {dollars_to_words(tab_state['total'])}. Ready to close out?")
            
            # Add to tab
            new_drink = {
                "sku": sku,
                "name": drink_data["name"],
                "description": drink_data["description"],
                "price": display_price,
                "quantity": quantity,
                "total": round(display_price * quantity, 2),
                "modifications": modifications,
                "category": category,
                "abv": drink_data["abv"],
                "original_price": price if is_happy_hour else None
            }
            
            # Check for existing item
            existing_item = None
            for item in tab_state["items"]:
                if item["sku"] == sku and item.get("modifications") == modifications:
                    existing_item = item
                    break
            
            if existing_item:
                existing_item["quantity"] += quantity
                existing_item["total"] = round(existing_item["price"] * existing_item["quantity"], 2)
                response = f"Added another {drink_data['name']}. You now have {existing_item['quantity']}."
            else:
                tab_state["items"].append(new_drink)
                response = f"Added {drink_data['name']} to your tab."
            
            # Update totals
            tab_state["subtotal"], tab_state["tax"], tab_state["total"] = calculate_totals(tab_state["items"])
            tab_state["item_count"] = sum(item["quantity"] for item in tab_state["items"])
            
            if drink_data["abv"] > 0:
                tab_state["alcoholic_drinks"] += quantity
                tab_state["last_drink_time"] = datetime.now().isoformat()
            
            # Add happy hour message if applied
            if is_happy_hour:
                response += f" Happy hour pricing applied - 20% off!"
            
            # Special message for water
            if sku == "N006":
                response = f"Added {drink_data['name']} to your tab. Stay hydrated!"
            elif tab_state['total'] > 0:
                response += f" Your tab is now {dollars_to_words(tab_state['total'])}."
            else:
                response += " No charge!"
            
            # Suggest water if needed
            if tab_state["alcoholic_drinks"] == 3:
                response += " Can I get you some water as well?"
            
            # Warning when approaching limits
            if current_count + quantity >= 15:
                response += f" Just so you know, we have a {MAX_DRINKS_PER_TAB} drink maximum."
            elif tab_state['total'] >= 150:
                response += f" Your tab is approaching our {dollars_to_words(MAX_TAB_AMOUNT)} limit."
            
            result = SwaigFunctionResult(response)
            save_tab_state(result, tab_state, global_data)
            
            # Send event to UI
            result.swml_user_event({
                "type": "drink_added",
                "drink": new_drink,
                "subtotal": tab_state["subtotal"],
                "tax": tab_state["tax"],
                "total": tab_state["total"],
                "item_count": tab_state["item_count"]
            })
            
            return result
        
        @self.tool(
            name="remove_drink",
            wait_file="/clearing.mp3",
            description="Remove a drink from the tab",
            parameters={
                "type": "object",
                "properties": {
                    "drink_name": {
                        "type": "string",
                        "description": "Name of drink to remove"
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "How many to remove (default: 1)",
                        "minimum": 1
                    }
                },
                "required": ["drink_name"]
            }
        )
        def remove_drink(args, raw_data):
            """Remove drink from tab"""
            tab_state, global_data = get_tab_state(raw_data)
            drink_name = args["drink_name"]
            quantity = args.get("quantity", 1)
            
            # Find and remove
            removed = False
            for i, item in enumerate(tab_state["items"]):
                if drink_name.lower() in item["name"].lower():
                    if item["quantity"] <= quantity:
                        if item["abv"] > 0:
                            tab_state["alcoholic_drinks"] -= item["quantity"]
                        tab_state["items"].pop(i)
                        response = f"Removed {item['name']} from your tab."
                    else:
                        item["quantity"] -= quantity
                        item["total"] = round(item["price"] * item["quantity"], 2)
                        if item["abv"] > 0:
                            tab_state["alcoholic_drinks"] -= quantity
                        response = f"Removed {quantity} {item['name']}. You still have {item['quantity']}."
                    removed = True
                    break
            
            if not removed:
                return SwaigFunctionResult(f"I couldn't find {drink_name} on your tab.")
            
            # Update totals
            tab_state["subtotal"], tab_state["tax"], tab_state["total"] = calculate_totals(tab_state["items"])
            tab_state["item_count"] = sum(item["quantity"] for item in tab_state["items"])
            
            result = SwaigFunctionResult(response)
            save_tab_state(result, tab_state, global_data)
            
            # Send event to UI
            result.swml_user_event({
                "type": "drink_removed",
                "drink_name": drink_name,
                "quantity": quantity,
                "subtotal": tab_state["subtotal"],
                "tax": tab_state["tax"],
                "total": tab_state["total"],
                "items": tab_state["items"]
            })
            
            return result
        
        @self.tool(
            name="review_tab",
            wait_file="/calculating.mp3",
            description="Review the current tab and show tip options when closing",
            parameters={
                "type": "object",
                "properties": {
                    "closing": {
                        "type": "boolean",
                        "description": "Set to true when customer is ready to close/pay"
                    }
                },
                "required": []
            }
        )
        def review_tab(args, raw_data):
            """Show current tab with tip options when closing"""
            tab_state, global_data = get_tab_state(raw_data)
            
            if not tab_state["items"]:
                return SwaigFunctionResult("Your tab is empty. What can I get for you?")
            
            # Check if we're in closing context
            is_closing = args.get("closing", False) or global_data.get("current_step") == "closing_tab"
            
            if is_closing:
                # Calculate tip options
                tip_18 = round(tab_state["subtotal"] * 0.18, 2)
                tip_20 = round(tab_state["subtotal"] * 0.20, 2)
                tip_25 = round(tab_state["subtotal"] * 0.25, 2)
                
                total_18 = round(tab_state["total"] + tip_18, 2)
                total_20 = round(tab_state["total"] + tip_20, 2)
                total_25 = round(tab_state["total"] + tip_25, 2)
                
                response = f"Your subtotal is {dollars_to_words(tab_state['subtotal'])}. "
                response += f"With tax, that's {dollars_to_words(tab_state['total'])}. "
                response += f"Adding 18% tip would be {dollars_to_words(total_18)}, "
                response += f"20% would be {dollars_to_words(total_20)}, "
                response += f"or 25% would be {dollars_to_words(total_25)}. "
                response += "Which would you prefer?"
                
                result = SwaigFunctionResult(response)
                
                result.swml_user_event({
                    "type": "tab_review",
                    "items": tab_state["items"],
                    "subtotal": tab_state["subtotal"],
                    "tax": tab_state["tax"],
                    "total": tab_state["total"],
                    "tip_suggestions": {
                        "18": {"amount": tip_18, "total": total_18},
                        "20": {"amount": tip_20, "total": total_20},
                        "25": {"amount": tip_25, "total": total_25}
                    }
                })
            else:
                # Regular tab review
                response = f"Your tab has {tab_state['item_count']} drinks. "
                response += f"Total is {dollars_to_words(tab_state['total'])} including tax."
                
                result = SwaigFunctionResult(response)
                
                result.swml_user_event({
                    "type": "tab_review",
                    "items": tab_state["items"],
                    "subtotal": tab_state["subtotal"],
                    "tax": tab_state["tax"],
                    "total": tab_state["total"]
                })
            
            return result
        
        @self.tool(
            name="check_happy_hour",
            description="Check if happy hour is active",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
        def check_happy_hour(args, raw_data):
            """Check happy hour status"""
            current_hour = datetime.now().hour
            is_active = 16 <= current_hour < 19
            
            if is_active:
                message = "Yes! It's happy hour! All cocktails are 20% off until 7 PM."
            elif current_hour < 16:
                message = f"Happy hour starts at 4 PM. Just {16 - current_hour} more hours!"
            else:
                message = "Happy hour ended at 7 PM. But our drinks are still worth full price!"
            
            result = SwaigFunctionResult(message)
            
            # Send event to UI to update happy hour banner
            result.swml_user_event({
                "type": "happy_hour_status",
                "active": is_active,
                "message": message
            })
            
            return result
        
        @self.tool(
            name="close_tab",
            wait_file="/payment.mp3",
            description="Close out the tab with customer's confirmed tip",
            parameters={
                "type": "object",
                "properties": {
                    "tip_percent": {
                        "type": "integer",
                        "description": "Customer's confirmed tip percentage (must be verified with customer first)",
                        "minimum": 0,
                        "maximum": 100
                    }
                },
                "required": ["tip_percent"]
            }
        )
        def close_tab(args, raw_data):
            """Close the tab and process payment"""
            tab_state, global_data = get_tab_state(raw_data)
            
            if not tab_state["items"]:
                return SwaigFunctionResult("Your tab is empty. Nothing to pay!")
            
            tip_percent = args.get("tip_percent", 0)
            tip_amount = round(tab_state["subtotal"] * (tip_percent / 100), 2)
            final_total = round(tab_state["total"] + tip_amount, 2)
            
            response = f"Perfect! Your total with a {tip_percent}% tip is {dollars_to_words(final_total)}. "
            response += "Thanks for coming to Outback Bar! Have a great night and get home safe!"
            
            # Clear the tab
            tab_state["items"] = []
            tab_state["subtotal"] = 0
            tab_state["tax"] = 0
            tab_state["total"] = 0
            tab_state["item_count"] = 0
            tab_state["alcoholic_drinks"] = 0
            
            result = SwaigFunctionResult(response)
            save_tab_state(result, tab_state, global_data)
            
            result.swml_user_event({
                "type": "tab_closed",
                "final_total": final_total,
                "tip_amount": tip_amount,
                "tip_percent": tip_percent
            })
            
            return result
    
    def get_app(self):
        """
        Override get_app to create custom app with all endpoints
        Following the Holy Guacamole pattern for consistency
        """
        if self._app is None:
            from fastapi import FastAPI, Request, Response
            from fastapi.middleware.cors import CORSMiddleware
            from fastapi.responses import FileResponse, JSONResponse
            from fastapi.staticfiles import StaticFiles
            
            # Create the FastAPI app
            app = FastAPI(
                title="Bartender AI Agent",
                description="AI-powered bartender assistant with Max"
            )
            
            # Add CORS middleware
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            
            # Set up paths
            from pathlib import Path
            self.bot_dir = Path(__file__).parent
            self.web_dir = self.bot_dir / "web"
            
            # API Routes (before static files so they take precedence)
            @app.get("/api/menu")
            async def get_menu():
                """Serve the drink menu from backend"""
                return JSONResponse(content={"menu": DRINKS})
            
            @app.get("/api/info")
            async def get_info():
                """Provide system information"""
                return JSONResponse(content={
                    "agent": self.get_name(),
                    "version": "1.0.0",
                    "endpoints": {
                        "ui": "/",
                        "menu": "/api/menu",
                        "happy_hour": "/api/happy-hour",
                        "swml": "/swml",
                        "swaig": "/swml/swaig",
                        "health": "/health"
                    }
                })
            
            @app.get("/health")
            async def health_check():
                return JSONResponse(content={
                    "status": "healthy",
                    "agent": self.get_name()
                })
            
            @app.get("/api/happy-hour")
            async def get_happy_hour():
                """Check if happy hour is active"""
                current_hour = datetime.now().hour
                is_active = 16 <= current_hour < 19
                return JSONResponse(content={
                    "active": is_active,
                    "discount": 0.20 if is_active else 0,
                    "message": "Happy Hour! 20% off cocktails!" if is_active else "Regular prices"
                })
            
            # Create router for SWML endpoints
            router = self.as_router()
            
            # Mount the SWML router at /swml
            app.include_router(router, prefix=self.route)
            
            # Add explicit handler for /swml (without trailing slash) since SignalWire posts here
            @app.post("/swml")
            async def handle_swml(request: Request, response: Response):
                """Handle POST to /swml - SignalWire's webhook endpoint"""
                return await self._handle_root_request(request)
            
            # Optionally also handle GET for testing
            @app.get("/swml")
            async def handle_swml_get(request: Request, response: Response):
                """Handle GET to /swml for testing"""
                return await self._handle_root_request(request)
            
            # Mount static files at root (this handles everything else)
            # The web directory contains all static files (HTML, JS, CSS, etc.)
            if self.web_dir.exists():
                app.mount("/", StaticFiles(directory=str(self.web_dir), html=True), name="static")
            
            self._app = app
        
        return self._app
    
    def serve(self, host=None, port=None):
        """
        Override serve to use our custom app
        Following the Holy Guacamole pattern
        """
        import uvicorn
        
        # Get host and port from parameters or defaults
        host = host or self.host or "0.0.0.0"
        port = port or self.port or 3030
        
        # Get our custom app with all endpoints
        app = self.get_app()
        
        # Get auth credentials for display
        username, password = self.get_basic_auth_credentials()
        
        # Print startup information
        print("=" * 60)
        print("🍸 Outback Bar - AI Bartender")
        print("=" * 60)
        print(f"\nServer: http://{host}:{port}")
        print(f"Basic Auth: {username}:{password}")
        print("\nEndpoints:")
        print(f"  Web UI:      http://{host}:{port}/")
        print(f"  Menu API:    http://{host}:{port}/api/menu")
        print(f"  Happy Hour:  http://{host}:{port}/api/happy-hour")
        print(f"  System API:  http://{host}:{port}/api/info")
        print(f"  SWML:        http://{host}:{port}/swml")
        print(f"  SWAIG:       http://{host}:{port}/swml/swaig")
        print(f"  Health:      http://{host}:{port}/health")
        print("=" * 60)
        print("\nPress Ctrl+C to stop\n")
        
        # Run the server
        try:
            uvicorn.run(app, host=host, port=port)
        except KeyboardInterrupt:
            print("\n🛑 Stopping Outback Bar server...")
            print("Thank you for visiting Outback Bar! 🍸")

if __name__ == "__main__":
    import os
    
    # Create agent instance
    agent = BartenderAgent()
    
    # Get port from environment variable or use 3030 as default
    port = int(os.environ.get('PORT', 3030))
    host = os.environ.get('HOST', '0.0.0.0')
    
    print(f"Starting server on {host}:{port}")
    agent.serve(host=host, port=port)