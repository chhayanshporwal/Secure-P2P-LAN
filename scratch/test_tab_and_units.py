import sys
import os
import tkinter as tk

SRC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from client_gui import format_size, format_speed, format_duration, format_eta, SecureClientGUI

def test_dynamic_units():
    print("Testing dynamic units...")
    assert format_size(0) == "0 B"
    assert format_size(512) == "512 B"
    assert format_size(2048) == "2.0 KB" or format_size(2048) == "2.00 KB"
    assert format_size(5 * 1024 * 1024) == "5.00 MB"
    assert format_size(int(2.5 * 1024 * 1024 * 1024)) == "2.50 GB"
    print("  -> format_size PASSED")

    assert format_speed(0) == "0.00 MB/s"
    assert format_speed(12.345) == "12.35 MB/s"
    assert format_speed(125.0) == "125.00 MB/s"
    print("  -> format_speed PASSED")

    assert format_duration(0) == "0s"
    assert format_duration(0.45) == "0.45s"
    assert format_duration(18) == "18sec"
    assert format_duration(184) == "3min 4sec"
    assert format_duration(60) == "1min"
    assert format_duration(3600) == "1hr"
    assert format_duration(4325) == "1hr 12min 5sec"
    print("  -> format_duration PASSED")

    assert format_eta(0) == "Done"
    assert format_eta(184) == "3min 4sec"
    assert format_eta(12) == "12sec"
    print("  -> format_eta PASSED")

def test_relative_tab_count():
    print("Testing relative tab counting logic...")
    root = tk.Tk()
    root.withdraw() # invisible
    app = SecureClientGUI(root)

    # Initial state: 1 tab
    assert len(app.send_tabs) == 1
    assert app.send_tabs[0].tab_id == 1
    assert app.sub_notebook.tab(app.send_tabs[0], "text").strip() == "Transfer #1"

    # Add Tab 2
    app.add_send_tab()
    assert len(app.send_tabs) == 2
    assert app.send_tabs[1].tab_id == 2
    assert app.sub_notebook.tab(app.send_tabs[1], "text").strip() == "Transfer #2"

    # Add Tab 3
    app.add_send_tab()
    assert len(app.send_tabs) == 3
    assert app.send_tabs[2].tab_id == 3
    assert app.sub_notebook.tab(app.send_tabs[2], "text").strip() == "Transfer #3"

    # Close Tab 2: Tab 3 should shift down to become Transfer #2
    tab2 = app.send_tabs[1]
    app.remove_send_tab(tab2)
    assert len(app.send_tabs) == 2
    assert app.send_tabs[0].tab_id == 1
    assert app.sub_notebook.tab(app.send_tabs[0], "text").strip() == "Transfer #1"
    assert app.send_tabs[1].tab_id == 2
    assert app.sub_notebook.tab(app.send_tabs[1], "text").strip() == "Transfer #2"
    print("  -> Closing Tab 2 successfully shifted remaining tab to Transfer #2!")

    # Now open another tab: it should say Transfer #3 (strictly sequential 1..N)
    app.add_send_tab()
    assert len(app.send_tabs) == 3
    assert app.send_tabs[2].tab_id == 3
    assert app.sub_notebook.tab(app.send_tabs[2], "text").strip() == "Transfer #3"
    print("  -> Adding new tab correctly became Transfer #3!")

    app.on_close()
    print("  -> Relative Tab Counting PASSED!")

if __name__ == "__main__":
    test_dynamic_units()
    test_relative_tab_count()
    print("\nALL TAB AND UNIT TESTS COMPLETED SUCCESSFULLY!")
