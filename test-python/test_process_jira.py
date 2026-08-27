import unittest

from process import componer_jql


class JiraQueryTest(unittest.TestCase):
    def test_adds_date_filters_before_order_by(self):
        jql = componer_jql(
            "project = WEB ORDER BY created DESC",
            start_date="2026-08-21",
            end_date="2026-08-27",
        )

        self.assertEqual(
            jql,
            '(project = WEB) AND created >= "2026-08-21" AND created < "2026-08-28" ORDER BY created DESC',
        )

    def test_keeps_base_jql_without_dates(self):
        self.assertEqual(componer_jql("project = WEB"), "project = WEB")


if __name__ == "__main__":
    unittest.main()
