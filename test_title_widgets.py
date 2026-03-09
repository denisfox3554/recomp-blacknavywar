import unittest

from title_widgets import SaveClearBtn


class _SaveConfirmCamel:
    class instance:
        calls = 0

        @classmethod
        def inOut(cls):
            cls.calls += 1


class _SaveConfirmSnake:
    class instance:
        calls = 0

        @classmethod
        def in_out(cls):
            cls.calls += 1


class SaveClearBtnTest(unittest.TestCase):
    def test_on_mouse_up_calls_save_confirm_in_out_camel(self):
        _SaveConfirmCamel.instance.calls = 0
        btn = SaveClearBtn(_SaveConfirmCamel)

        btn.on_mouse_up()

        self.assertTrue(btn.super_called)
        self.assertEqual(_SaveConfirmCamel.instance.calls, 1)

    def test_on_mouse_up_calls_save_confirm_in_out_snake(self):
        _SaveConfirmSnake.instance.calls = 0
        btn = SaveClearBtn(_SaveConfirmSnake)

        btn.on_mouse_up()

        self.assertTrue(btn.super_called)
        self.assertEqual(_SaveConfirmSnake.instance.calls, 1)


if __name__ == "__main__":
    unittest.main()
