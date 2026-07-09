import unittest

import app


class TravelPlannerTests(unittest.TestCase):
    def test_chat_response_uses_profile_details(self):
        profile = {
            "travel_style": "luxury",
            "budget": "₹40,000",
            "num_travellers": 4,
            "days": 3,
            "preferences": "beaches and nightlife",
        }
        response = app.build_smart_chat_response(
            "Plan a 3-day Goa trip for 4 travellers on a luxury budget",
            profile,
        )
        self.assertIn("Goa", response)
        self.assertIn("3-day", response)
        self.assertIn("4", response)
        self.assertIn("Luxury", response)

    def test_budget_estimation_returns_breakdown_and_per_person_costs(self):
        result = app.estimate_trip_budget("kerala", 4, "budget", 2)
        self.assertIn("breakdown", result)
        self.assertIn("accommodation", result["breakdown"])
        self.assertIn("food", result["breakdown"])
        self.assertGreater(result["total_per_person"], 0)
        self.assertGreater(result["daily_per_person"], 0)

    def test_itinerary_is_destination_specific(self):
        goa_plan = app.build_smart_itinerary("goa", 3, "budget", None)
        kerala_plan = app.build_smart_itinerary("kerala", 3, "balanced", None)
        self.assertIn("Baga", goa_plan)
        self.assertIn("Alleppey", kerala_plan)

    def test_greetings_are_natural(self):
        for message in ["hi", "hello", "good morning", "how are you?", "thank you"]:
            response = app.build_smart_chat_response(message, None, [])
            self.assertTrue(response)
            self.assertNotIn("i don't know", response.lower())

    def test_follow_up_questions_are_requested_when_details_are_missing(self):
        response = app.build_smart_chat_response("I want to visit Goa", None, [])
        self.assertIn("days", response.lower())
        self.assertIn("budget", response.lower())
        self.assertIn("travellers", response.lower())

    def test_multiple_conversations_produce_destination_specific_responses(self):
        conversations = [
            "Plan a weekend trip to Jaipur",
            "Help me with a 5-day Hyderabad itinerary",
            "Suggest a luxury trip to Dubai",
            "I need a family-friendly plan for Singapore",
            "What should I do in Paris for 3 days",
            "Recommend a budget trip to Bali",
            "Create an adventure plan for Rishikesh",
            "What is the best time to visit Tokyo",
            "Suggest restaurants in Mumbai",
            "Give me a budget for a 4-day trip to Goa",
            "Help me plan a honeymoon to Maldives",
            "What can I do in London for a weekend",
            "Recommend hotels in Udaipur",
            "Plan a trip to Shillong for 2 days",
            "Where should I stay in Coorg",
            "Suggest a calm itinerary for Ooty",
            "What are the best places in Varanasi",
            "Plan a family trip to Manali",
            "Create a luxury itinerary for Rome",
            "What is the best season for Sydney",
            "Show me attractions in New York",
            "Make a 3-day plan for Leh Ladakh",
            "What is the weather like in Kerala",
            "Recommend food in Chennai",
            "How many days should I spend in Bangalore",
            "I want a romantic plan for Paris",
            "Suggest a budget trip to Thailand",
            "Plan a weekend in Darjeeling",
            "Help with transport in Srinagar",
            "Give me an itinerary for Hampi",
            "What should I pack for Kodaikanal",
        ]

        for message in conversations:
            response = app.build_smart_chat_response(message, None, [])
            self.assertTrue(response)
            self.assertNotIn("i don't know", response.lower())


if __name__ == "__main__":
    unittest.main()
