import unittest
from main import Stock_Name_Check, Chart_Type, Time_Series, Dates


class LearnTest(unittest.TestCase):

    

    def test_Stock_Name_Check(self):
        
        #valid
        self.assertEqual(Stock_Name_Check("appl"), 1)
        self.assertEqual(Stock_Name_Check("Appl"), 1)

        #invalid
        self.assertEqual(Stock_Name_Check("applesinthefarm"), 0)
        self.assertEqual(Stock_Name_Check("appl23091ndewjxs"), 0)

    
    def test_chart_type(self):
        #valid
        self.assertEqual(Chart_Type("1"), 1)
        self.assertEqual(Chart_Type("2"), 1)

        #invalid
        self.assertEqual(Chart_Type("3"), 0)
        self.assertEqual(Chart_Type("2a"), 0)
        self.assertEqual(Chart_Type("a"), 0)

    def test_times_series(self):
        #valid
        self.assertEqual(Time_Series("1"), 1)
        self.assertEqual(Time_Series("2"), 1)
        self.assertEqual(Time_Series("3"), 1)
        self.assertEqual(Time_Series("4"), 1)

        #invalid
        self.assertEqual(Time_Series("5"), 0)
        self.assertEqual(Time_Series("-1"), 0)
        self.assertEqual(Time_Series("a"), 0)
        self.assertEqual(Time_Series("1a"), 0)


    #DATES TESTING

    def test_valid_iso_format(self):
        status, start, end = Dates("2023-01-01", "2023-12-31")
        self.assertEqual(status, 1)
        self.assertEqual(start, "2023-01-01")
        self.assertEqual(end, "2023-12-31")

    def test_valid_alternate_format(self):
        status, start, end = Dates("01/01/2023", "12/31/2023")
        self.assertEqual(status, 1)
        self.assertEqual(start, "2023-01-01")
        self.assertEqual(end, "2023-12-31")

    def test_swap_dates(self):
        status, start, end = Dates("2023-12-31", "2023-01-01")
        self.assertEqual(status, 1)
        self.assertEqual(start, "2023-01-01")
        self.assertEqual(end, "2023-12-31")

    def test_invalid_format(self):
        status, start, end = Dates("2023.01.01", "2023.12.31")
        self.assertEqual(status, 0)
        self.assertIsNone(start)
        self.assertIsNone(end)

    def test_missing_date(self):
        status, start, end = Dates("", "2023-12-31")
        self.assertEqual(status, 0)
        self.assertIsNone(start)
        self.assertIsNone(end)




        



if __name__ == "__main__":
    unittest.main()


