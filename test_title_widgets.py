import unittest

from title_widgets import SaveClearBtn, SaveConfirm, TitleCredistBtn, TitleDemoBtn


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


class SaveConfirmTest(unittest.TestCase):
    def test_constructor_sets_static_instance(self):
        SaveConfirm.instance = None

        confirm = SaveConfirm()

        self.assertIs(SaveConfirm.instance, confirm)

    def test_on_remove_clears_static_instance(self):
        confirm = SaveConfirm()

        confirm.on_remove()

        self.assertIsNone(SaveConfirm.instance)

    def test_in_out_from_init_goes_to_init_label_and_moving(self):
        confirm = SaveConfirm()

        confirm.in_out()

        self.assertEqual(confirm.timeline_calls, ["init"])
        self.assertEqual(confirm.status, SaveConfirm.MOVING)

    def test_in_out_from_display_goes_to_hide_label_and_moving(self):
        confirm = SaveConfirm(status=SaveConfirm.DISPLAY)

        confirm.inOut()

        self.assertEqual(confirm.timeline_calls, ["hide"])
        self.assertEqual(confirm.status, SaveConfirm.MOVING)

    def test_in_out_from_moving_does_nothing(self):
        confirm = SaveConfirm(status=SaveConfirm.MOVING)

        confirm.in_out()

        self.assertEqual(confirm.timeline_calls, [])
        self.assertEqual(confirm.status, SaveConfirm.MOVING)


if __name__ == "__main__":
    unittest.main()


class _DocRootCamel:
    class instance:
        calls = []

        @classmethod
        def gotoAndPlay(cls, label: str):
            cls.calls.append(label)


class _DocRootSnake:
    class instance:
        calls = []

        @classmethod
        def goto_and_play(cls, label: str):
            cls.calls.append(label)


class TitleCredistBtnTest(unittest.TestCase):
    def test_on_mouse_up_transitions_to_credits_camel(self):
        _DocRootCamel.instance.calls = []
        btn = TitleCredistBtn(_DocRootCamel)

        btn.on_mouse_up()

        self.assertTrue(btn.super_called)
        self.assertEqual(_DocRootCamel.instance.calls, ["credits"])

    def test_on_mouse_up_transitions_to_credits_snake(self):
        _DocRootSnake.instance.calls = []
        btn = TitleCredistBtn(_DocRootSnake)

        btn.on_mouse_up()

        self.assertTrue(btn.super_called)
        self.assertEqual(_DocRootSnake.instance.calls, ["credits"])


class TitleDemoBtnTest(unittest.TestCase):
    def test_on_mouse_up_transitions_to_demo_camel(self):
        _DocRootCamel.instance.calls = []
        btn = TitleDemoBtn(_DocRootCamel)

        btn.on_mouse_up()

        self.assertTrue(btn.super_called)
        self.assertEqual(_DocRootCamel.instance.calls, ["demo"])

    def test_on_mouse_up_transitions_to_demo_snake(self):
        _DocRootSnake.instance.calls = []
        btn = TitleDemoBtn(_DocRootSnake)

        btn.on_mouse_up()

        self.assertTrue(btn.super_called)
        self.assertEqual(_DocRootSnake.instance.calls, ["demo"])
