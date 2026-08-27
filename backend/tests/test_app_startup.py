import unittest
from unittest.mock import patch

import app.main as main


class StartupInitializationTests(unittest.TestCase):
    @patch.object(main, "seed_products")
    @patch.object(main, "seed_admins")
    @patch.object(main.Base.metadata, "create_all")
    @patch.object(main.scheduler, "start")
    @patch.object(main.scheduler, "add_job")
    def test_initialize_app_is_idempotent(self, mock_add_job, mock_scheduler_start, mock_create_all, mock_seed_admins, mock_seed_products):
        main.initialize_app()
        main.initialize_app()

        self.assertEqual(mock_create_all.call_count, 1)
        self.assertEqual(mock_seed_products.call_count, 1)
        self.assertEqual(mock_seed_admins.call_count, 1)
        self.assertEqual(mock_add_job.call_count, 1)
        self.assertEqual(mock_scheduler_start.call_count, 1)


if __name__ == "__main__":
    unittest.main()
