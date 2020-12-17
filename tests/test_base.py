"""Unit tests for the jgt_common tools."""

from itertools import product, cycle
import tempfile
from math import nan
from uuid import uuid4
from os import path, mkdir
import random
import re
import shutil
import string

import pytest
import jgt_common


TEST_MESSAGE = "Test Message"
CYCLE_MIDDLE_ITEM = 2
CYCLE_ITEMS = [1, CYCLE_MIDDLE_ITEM, 3]
CYCLE_OF_NUMBERS = cycle(CYCLE_ITEMS)
CHECK_UNTIL_TIMEOUT = 2
CHECK_UNTIL_CYCLE_SECS = 0.1


@pytest.fixture
def list_for_padding():
    """Return a short list to be used to pad into a longer list."""
    return ["a", "b"]


@pytest.fixture
def temp_dir():
    """Create and return a tmpdir for testing."""
    log_dir = tempfile.mkdtemp()
    yield log_dir
    shutil.rmtree(log_dir)


@pytest.fixture
def temp_dir_with_name_file():
    dir_path = tempfile.mkdtemp()
    with open(path.join(dir_path, "display_name.txt"), "w") as f:
        f.write(TEST_MESSAGE)
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def unique_dict():
    return {
        uuid4(): uuid4() for x in range(5)
    }  # arbitrary, length > 1 and "not too big"


@pytest.fixture
def unique_list():
    return [uuid4() for x in range(5)]  # arbitrary length, chosen to match unique_dict


PACKAGE_NAMES = {
    None: "Test Directory",
    "test.package.name_for_testing": "Name For Testing",
}


@pytest.mark.parametrize("package_name_and_expected", PACKAGE_NAMES.items())
def test_display_name_without_name_file(temp_dir, package_name_and_expected):
    package_name, expected = package_name_and_expected
    target_dir = path.join(temp_dir, "test_directory")
    mkdir(target_dir)
    display_name = jgt_common.display_name(target_dir, package_name)
    assert display_name == expected


@pytest.mark.parametrize("package_name", PACKAGE_NAMES.keys())
def test_display_name_with_name_file(temp_dir_with_name_file, package_name):
    display_name = jgt_common.display_name(temp_dir_with_name_file, package_name)
    assert display_name == TEST_MESSAGE


DICT_STRIP_VALUES = ["", None, "None", 1234, []]
DIST_STRIP_CASES = [
    ({uuid4(): x for x in DICT_STRIP_VALUES}, y) for y in DICT_STRIP_VALUES
]


@pytest.mark.parametrize("dict_to_strip,value_to_strip", DIST_STRIP_CASES)
def test_dict_strip_valid_values_remain(dict_to_strip, value_to_strip):
    stripped_dictionary = jgt_common.dict_strip_value(
        dict_to_strip, value=value_to_strip
    )
    for valid_value in [x for x in DICT_STRIP_VALUES if x != value_to_strip]:
        assert valid_value in stripped_dictionary.values()


@pytest.mark.parametrize("dict_to_strip,value_to_strip", DIST_STRIP_CASES)
def test_dict_strip_stripped_values_are_gone(dict_to_strip, value_to_strip):
    stripped_dictionary = jgt_common.dict_strip_value(
        dict_to_strip, value=value_to_strip
    )
    assert value_to_strip not in stripped_dictionary.values()


@pytest.mark.parametrize("dict_to_filter,value_to_keep", DIST_STRIP_CASES)
def test_filter_dict_keep_value(dict_to_filter, value_to_keep):
    new_dict = jgt_common.filter_dict(
        dict_to_filter, keep_value=lambda x: x == value_to_keep
    )
    assert all(map(lambda x: x == value_to_keep, new_dict.values()))


def test_filter_dict_noop(unique_dict):
    new_dict = jgt_common.filter_dict(unique_dict)
    assert new_dict == unique_dict
    assert new_dict is not unique_dict


def test_filter_dict_keep_key(unique_dict):
    all_keys = list(unique_dict.keys())
    for key_to_keep in all_keys:
        new_dict = jgt_common.filter_dict(
            unique_dict, keep_key=lambda x: x == key_to_keep
        )
        assert len(new_dict) == 1
        assert key_to_keep in new_dict


def test_filter_dict_keep_nothing_by_key(unique_dict):
    new_dict = jgt_common.filter_dict(unique_dict, keep_key=jgt_common.always_false)
    assert new_dict == {}


def test_filter_dict_keep_nothing_by_value(unique_dict):
    new_dict = jgt_common.filter_dict(unique_dict, keep_value=jgt_common.always_false)
    assert new_dict == {}


def test_filter_dict_keep_nothing_by_key_and_value(unique_dict):
    new_dict = jgt_common.filter_dict(
        unique_dict,
        keep_key=jgt_common.always_false,
        keep_value=jgt_common.always_false,
    )
    assert new_dict == {}


def test_dict_transform_noop(unique_dict):
    new_dict = jgt_common.dict_transform(unique_dict)
    assert new_dict == unique_dict


def test_dict_transform_monokey(unique_dict):
    new_key = uuid4()
    new_dict = jgt_common.dict_transform(unique_dict, key_transform=lambda x: new_key)
    assert len(new_dict) == 1
    assert new_key in new_dict


def test_dict_transform_monovalue(unique_dict):
    new_value = uuid4()
    new_dict = jgt_common.dict_transform(
        unique_dict, value_transform=lambda x: new_value
    )
    assert len(new_dict) == len(unique_dict)
    assert set(new_dict.values()) == {new_value}


def test_dict_from(unique_list):
    new_dict = jgt_common.dict_from(
        unique_list, value_transform=lambda x: "My value is {}".format(x)
    )
    assert len(new_dict) == len(unique_list)
    assert set(new_dict.keys()) == set(unique_list)
    assert all(v == "My value is {}".format(k) for k, v in new_dict.items())


PADDED_LIST_CASES = list(product([0, 5, 15], [None, "TEST"]))


@pytest.mark.parametrize("target_length,padding", PADDED_LIST_CASES)
def test_padding_length(list_for_padding, target_length, padding):
    padded = jgt_common.padded_list(list_for_padding, target_length, padding=padding)
    assert len(padded) == target_length


@pytest.mark.parametrize("target_length,padding", PADDED_LIST_CASES)
def test_padding_value(list_for_padding, target_length, padding):
    padded = jgt_common.padded_list(list_for_padding, target_length, padding=padding)
    assert padded.count(padding) == max(target_length - len(list_for_padding), 0)


def _cleanup_and_exit(dir_path=None):
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        jgt_common.cleanup_and_exit(dir_name=dir_path)
    assert pytest_wrapped_e.value.code == 0


def test_cleanup_and_exit_without_dir():
    _cleanup_and_exit()


def test_cleanup_and_exit_with_dir():
    dir_path = tempfile.mkdtemp()
    _cleanup_and_exit(dir_path=dir_path)
    assert not path.exists(dir_path)


def test_index_or_default_value_in_list():
    assert jgt_common.index_or_default([1, 2, 3], 2) == 1


def test_index_or_default_value_not_present():
    assert jgt_common.index_or_default([1, 2, 3], 5) == -1


def test_index_or_default_custom_default():
    assert jgt_common.index_or_default([1, 2, 3], 5, default=99) == 99


def test_no_virtual_env(monkeypatch):
    # Don't depend on tests being run in, or not run in, a virtual environment.
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    arbitrary_exit_code = 45
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        jgt_common.must_be_in_virtual_environment(exit_code=arbitrary_exit_code)
    assert pytest_wrapped_e.value.code == arbitrary_exit_code


def test_virtual_env(monkeypatch):
    # Don't depend on tests being run in, or not run in, a virtual environment.
    monkeypatch.setenv("VIRTUAL_ENV", "arbitrary_value")
    arbitrary_exit_code = 45
    # If this next function call exits, pytest will report an error:
    jgt_common.must_be_in_virtual_environment(exit_code=arbitrary_exit_code)


def test_safe_run_passing():
    # This should not raise any exceptions (pytest will fail the test if it does)
    jgt_common.safe_run(["ls"])


@pytest.mark.parametrize(
    "command,expected_exit_codes",
    [
        ("asdfadssfl", (-1,)),  # A nonexistent command will raise an OSError
        (
            "ls asdfsdfsfs",
            (1, 2),  # Mac exit code  # Centos Exit code
        ),  # A call to list a nonexistent directory will return a nonzero exit code
    ],
)
def test_safe_run_with_fail(command, expected_exit_codes):
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        jgt_common.safe_run(command.split())
    assert pytest_wrapped_e.value.code in expected_exit_codes


TEST_EXIT_CODES = [-1, 0, 1]


@pytest.mark.parametrize("exit_code", TEST_EXIT_CODES)
def test_exit_without_message(capsys, exit_code):
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        jgt_common.exit(status=exit_code)
    assert pytest_wrapped_e.value.code == exit_code


@pytest.mark.parametrize("exit_code", TEST_EXIT_CODES)
def test_exit_with_message(capsys, exit_code):
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        jgt_common.exit(status=exit_code, message=TEST_MESSAGE)
    assert pytest_wrapped_e.value.code == exit_code
    out, err = capsys.readouterr()
    assert TEST_MESSAGE in err


WITHOUT_CHECK_VALUES = list(product([None, "", 0], TEST_EXIT_CODES, ["", TEST_MESSAGE]))


@pytest.mark.parametrize("check,exit_code,message", WITHOUT_CHECK_VALUES)
def test_error_if_without_check(check, exit_code, message):
    jgt_common.error_if(check, status=exit_code, message=message)


WITH_CHECK_VALUES = list(product(["Error", 1, -1], TEST_EXIT_CODES, ["", TEST_MESSAGE]))


@pytest.mark.parametrize("check,exit_code,message", WITH_CHECK_VALUES)
def test_error_if_with_check(capsys, check, exit_code, message):
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        jgt_common.error_if(check, status=exit_code, message=message)
    out, err = capsys.readouterr()
    assert message in err
    assert pytest_wrapped_e.value.code == exit_code or check


RANDOM_STRING_DEFAULT_SIZE = 8
RANDOM_STRING_DEFAULT_CHOOSE_FROM = string.ascii_lowercase + string.digits


def test_random_string_length():
    non_default_size = RANDOM_STRING_DEFAULT_SIZE + 5
    text = jgt_common.generate_random_string(size=non_default_size)
    assert len(text) == non_default_size


def test_random_string_prefix():
    prefix = "test-"
    text = jgt_common.generate_random_string(prefix=prefix)
    assert text.startswith(prefix)


def test_random_string_suffix():
    suffix = "-test"
    text = jgt_common.generate_random_string(suffix=suffix)
    assert text.endswith(suffix)


def test_random_string_choose_from():
    # Using only symbols to avoid any overlap with the default choose_from
    non_default_choose_from = "(_)+-*&$#@"
    text = jgt_common.generate_random_string(choose_from=non_default_choose_from)
    assert set(text) <= set(non_default_choose_from)


def test_random_string_default_size():
    text = jgt_common.generate_random_string()
    assert len(text) == RANDOM_STRING_DEFAULT_SIZE


def test_random_string_default_choose_from():
    text = jgt_common.generate_random_string()
    assert set(text) <= set(RANDOM_STRING_DEFAULT_CHOOSE_FROM)


def test_string_size_failure():
    with pytest.raises(AssertionError):
        jgt_common.generate_random_string(
            prefix="this-is-a-long-prefix-", suffix="-this-is-a-long-suffix", size=3
        )


KEY_TEST_DICT = {"a": 1, 1: "a", "key": "value", "nested": {"a": 5}}


def _sorted_key_names(dict_):
    return sorted(map(str, dict_))


def test_valid_key():
    key = random.choice(list(KEY_TEST_DICT.keys()))
    value = jgt_common.must_get_key(KEY_TEST_DICT, key)
    assert value == KEY_TEST_DICT[key]


def test_invalid_key():
    key = jgt_common.generate_random_string()
    expected_msg = "{} is not one of: {}".format(key, _sorted_key_names(KEY_TEST_DICT))
    with pytest.raises(KeyError, match=expected_msg):
        jgt_common.must_get_key(KEY_TEST_DICT, key)


def test_valid_keys():
    value = jgt_common.must_get_keys(KEY_TEST_DICT, "nested", "a")
    assert value == KEY_TEST_DICT["nested"]["a"]


def test_invalid_keys():
    key = jgt_common.generate_random_string()
    expected_msg = "{} is not one of: {}".format(
        key, _sorted_key_names(KEY_TEST_DICT["nested"])
    )
    with pytest.raises(KeyError, match=expected_msg):
        jgt_common.must_get_keys(KEY_TEST_DICT, "nested", key)


FORMAT_STR = "Test format string: {}"


def test_format_if_with_content():
    value = "test value"
    assert jgt_common.format_if(FORMAT_STR, value) == FORMAT_STR.format(value)


def test_format_if_no_content():
    value = None
    assert jgt_common.format_if(FORMAT_STR, value) == ""


def test_default_if_none_with_content():
    # Pick a falsey value to make sure only None is being checked for.
    falsey_value = ""
    truthy_value = 57
    assert jgt_common.default_if_none(falsey_value, truthy_value) == falsey_value


def test_default_if_none_with_none():
    arbitrary_default = 57  # Anything except None
    assert jgt_common.default_if_none(None, arbitrary_default) == arbitrary_default


FALSEY_VALUES = [None, "", [], {}, False, 0]
SINGLE_ITEM_VALUES = [1, 11111, "1", "ABCDEFG", "ABCDEFG", [[]], {"A": 1, "B": 2}, True]
ITERABLE_VALUES = [
    [1, 2, 3],
    list("abcde"),
    [[1], [2], [3]],
    map(lambda x: x, [1, 2, 3]),
    {1, 2},
]


@pytest.mark.parametrize("falsey_items", FALSEY_VALUES)
def test_list_from_empty_values(falsey_items):
    assert jgt_common.list_from(falsey_items) == []


@pytest.mark.parametrize("single_items", SINGLE_ITEM_VALUES)
def test_list_from_single_items(single_items):
    assert len(jgt_common.list_from(single_items)) == 1


@pytest.mark.parametrize("iterable_items", ITERABLE_VALUES)
def test_list_from_iterable(iterable_items):
    results = jgt_common.list_from(iterable_items)
    assert len(results) > 1
    for item in iterable_items:
        assert item in results


def test_no_nones():
    assert None not in jgt_common.no_nones(FALSEY_VALUES)


def test_truths_from():
    assert jgt_common.truths_from(FALSEY_VALUES) == []
    assert (
        jgt_common.truths_from(FALSEY_VALUES + SINGLE_ITEM_VALUES) == SINGLE_ITEM_VALUES
    )


def test_get_file_contents(temp_dir):
    file_path = path.join(temp_dir, "test.txt")
    with open(file_path, "w") as f:
        f.write(TEST_MESSAGE)
    assert jgt_common.get_file_contents(file_path) == TEST_MESSAGE


def test_get_file_docstring():
    assert jgt_common.get_file_docstring(__file__) == __doc__


def _is_vowel(value):
    return value.lower() in ["a", "e", "i", "o", "u"]


FILTER_LINES_DATA = [
    # (input, expected_output, line_filter, output)
    ("A\nB\nC\nD\nE", "A\nE", _is_vowel, None),  # str -> str
    ("A\nB\nC\nD\nE", ["A", "E"], _is_vowel, list),  # str -> list
    (["A", "B", "C", "D", "E"], ["A", "E"], _is_vowel, None),  # list -> list
    (["A", "B", "C", "D", "E"], "A\nE", _is_vowel, str),  # list -> str
]


@pytest.mark.parametrize(
    "input_,expected_output,line_filter,return_type", FILTER_LINES_DATA
)
def test_filter_lines_given_str(input_, expected_output, line_filter, return_type):
    output = jgt_common.filter_lines(line_filter, input_, return_type)
    assert output == expected_output


STRING_TO_LIST_DATA = {
    "  This is a simple space separated list": {
        "kwargs": {"sep": None},
        "results": ["This", "is", "a", "simple", "space", "separated", "list"],
    },
    " Sample value, from, a, config, file ": {
        "kwargs": {},
        "results": ["Sample value", "from", "a", "config", "file"],
    },
    " plus-separated+string+here": {
        "kwargs": {"sep": "+"},
        "results": ["plus-separated", "string", "here"],
    },
    " -strike-through-=-another-=-word-,=blah== ": {
        "kwargs": {"sep": "=", "maxsplit": 2, "chars": "-"},
        "results": [" -strike-through", "another", "word-,=blah== "],
    },
}


@pytest.mark.parametrize("source,test_data", STRING_TO_LIST_DATA.items())
def test_string_to_list(source, test_data):
    assert (
        jgt_common.string_to_list(source, **test_data["kwargs"]) == test_data["results"]
    )


def test_fib_or_max():
    # All numbers chosen here are arbitrary
    assert jgt_common.fib_or_max(0, 30) == 0
    assert jgt_common.fib_or_max(6, 30) == 8
    assert jgt_common.fib_or_max(1000, 30) == 30


def make_retry_helper(retry_count, exceptions_to_catch, max_retry_sleep):
    @jgt_common.retry_on_exceptions(retry_count, exceptions_to_catch, max_retry_sleep)
    def function_that_might_throw(exception, counter_list_hack):
        counter_list_hack[0] += 1
        if exception:
            raise exception

    return function_that_might_throw


def test_retry_on_exception():
    # All these are arbitrary, but...
    # keep the retry count and sleep time low so tests don't take too long to run.
    retry_count = 3
    helper_that_might_throw = make_retry_helper(retry_count, (KeyError, NameError), 2)

    # No exception, should only be called once.
    counter = [0]
    helper_that_might_throw(None, counter)
    assert counter[0] == 1

    # uncaught exception, should only be called once.
    arbitrary_exception = IndexError  # Anything not listed above...
    counter = [0]
    with pytest.raises(IndexError):
        helper_that_might_throw(IndexError, counter)
    assert counter[0] == 1

    # caught exceptions, make sure retry count is correct.
    counter = [0]
    arbitrary_exception = KeyError
    with pytest.raises(arbitrary_exception):
        helper_that_might_throw(arbitrary_exception, counter)

    # <n> retries means <n>+1 calls
    assert counter[0] == retry_count + 1


def test_retry_on_exception_error_handling():
    with pytest.raises(AssertionError) as e:
        make_retry_helper(10, None, 1)
    # Make sure we get the right error, but don't lock down the exact error
    # string raised.
    assert "No exception" in str(e)

    with pytest.raises(AssertionError) as e:
        make_retry_helper(0, KeyError, 1)
    # Make sure we get the right error, but don't lock down the exact error
    # string raised.
    assert "max_retry_count must be" in str(e)


def cycle_func():
    return next(CYCLE_OF_NUMBERS)


def is_final_number(n):
    return n == CYCLE_ITEMS[-1]


def test_check_until_function_call_is_only_invoked_once_if_first_call_succeeds():
    call_log = []
    arbitrary_but_non_trivial_timeout = 10
    arbitrary_but_non_trivial_cycle_secs = 1
    arbitrary_fn_args = (1,)
    jgt_common.check_until(
        call_log.append,
        lambda *args: True,
        fn_args=arbitrary_fn_args,
        timeout=arbitrary_but_non_trivial_timeout,
        cycle_secs=arbitrary_but_non_trivial_cycle_secs,
    )
    assert (
        len(call_log) == 1
    ), "check_until invoked function_call the wrong number of times!"


def test_check_until_pass():
    assert (
        jgt_common.check_until(
            cycle_func,
            is_final_number,
            timeout=CHECK_UNTIL_TIMEOUT,
            cycle_secs=CHECK_UNTIL_CYCLE_SECS,
        )
        == CYCLE_ITEMS[-1]
    )


def test_check_until_never():
    with pytest.raises(jgt_common.IncompleteAtTimeoutException) as e:
        jgt_common.check_until(
            cycle_func,
            jgt_common.always_false,
            timeout=CHECK_UNTIL_TIMEOUT,
            cycle_secs=CHECK_UNTIL_CYCLE_SECS,
        )
        assert e.call_result in CYCLE_ITEMS
        assert e.timeout == CHECK_UNTIL_TIMEOUT


def test_check_while():
    assert (
        jgt_common.check_while(
            cycle_func,
            lambda r: r != CYCLE_MIDDLE_ITEM,
            timeout=CHECK_UNTIL_TIMEOUT,
            cycle_secs=CHECK_UNTIL_CYCLE_SECS,
        )
        == CYCLE_MIDDLE_ITEM
    )


def test_only_item_of():
    bad_lists = [[], list(range(100))]
    for bad_list in bad_lists:
        with pytest.raises(AssertionError):
            jgt_common.only_item_of(bad_list)

    assert jgt_common.only_item_of([1]) == 1


def test_simple_responseinfo_data():
    response = jgt_common.generate_random_string()
    description = jgt_common.generate_random_string()
    extra_field = jgt_common.generate_random_string()
    a_response = jgt_common.ResponseInfo(
        response=response, description=description, extra_field=extra_field
    )
    assert a_response.response == response
    assert a_response.description == description
    assert a_response.extra_field == extra_field
    # No callbacks, so the response data should just be the response
    assert a_response.response_data == response


# Testing helpers for the ResponseInfo callback mechanism.

# Keep track of how many times the callback has been invoked.
# Using the usual list hack to avoid global variable declarations and annoyances.
arbitrary_callback_counter = [0]

ARBITRARY_CALLBACK_VALUE = "phone number 867-5329"


@pytest.fixture
def random_string():
    """
    Generate a random string.

    Build something arbitrary and random that doesn't collide with
    ARBITRARY_CALLBACK_VALUE
    """
    # making the value larger ensures it won't collide.
    return jgt_common.generate_random_string(size=len(ARBITRARY_CALLBACK_VALUE) + 1)


def arbitrary_callback():
    arbitrary_callback_counter[0] += 1
    return ARBITRARY_CALLBACK_VALUE


def test_callback_response_data(random_string):
    a_response = jgt_common.ResponseInfo(
        response=random_string, response_callback=arbitrary_callback
    )
    assert a_response.response_data == ARBITRARY_CALLBACK_VALUE

    # Now make sure .response has been changed:
    assert a_response.response == ARBITRARY_CALLBACK_VALUE


def test_callback_response_data_callback_only_called_once():
    a_response = jgt_common.ResponseInfo(response_callback=arbitrary_callback)

    arbitrary_callback_counter[0] = 0
    a_response.run_response_callback()

    assert a_response.response == ARBITRARY_CALLBACK_VALUE
    assert arbitrary_callback_counter[0] == 1

    a_response.run_response_callback()
    assert a_response.response == ARBITRARY_CALLBACK_VALUE
    assert arbitrary_callback_counter[0] == 1


def test_extract_response_data():
    arbitrary_string = "arbitrary_string".lower()
    a_response = jgt_common.ResponseInfo(
        response=arbitrary_string, response_data_extract=str.swapcase
    )
    assert a_response.response_data == arbitrary_string.swapcase()


def test_extract_and_callback_response_data(random_string):
    a_response = jgt_common.ResponseInfo(
        response=random_string,
        response_callback=arbitrary_callback,
        response_data_extract=str.swapcase,
    )
    assert a_response.response_data == ARBITRARY_CALLBACK_VALUE.swapcase()


def test_empty_notemptylist_errors_out():
    with pytest.raises(AssertionError):
        for item in jgt_common.NotEmptyList():
            pass


def test_mundane_notemptylist():
    arbitrary_list_len = random.randint(1, 10)  # Anything > 0 is fine.
    my_list = jgt_common.NotEmptyList()
    my_list.extend(range(arbitrary_list_len))
    for item in my_list:
        pass  # make sure no exception thrown.
    assert my_list == list(range(arbitrary_list_len))


def test_commonattributelist_attr_access():
    arbitrary_list_len = random.randint(1, 10)  # Anything > 0 is fine.
    my_list = jgt_common.CommonAttributeList()
    for x in range(arbitrary_list_len):
        my_list.append(jgt_common.ResponseInfo(data=x))
    assert my_list.data == list(range(arbitrary_list_len))


def test_commonattributelist_attr_set(random_string):
    arbitrary_list_len = random.randint(1, 10)  # Anything > 0 is fine.
    my_list = jgt_common.CommonAttributeList()

    # First set up different data for each item
    for x in range(arbitrary_list_len):
        my_list.append(jgt_common.ResponseInfo(data=x))

    # overwrite data with the same value.
    my_list.data = random_string

    # make sure new value is consisten across each element.
    assert my_list.data == [random_string] * arbitrary_list_len


def test_commonattributelist_update_all(random_string):
    arbitrary_list_len = random.randint(1, 10)  # Anything > 0 is fine.
    my_list = jgt_common.CommonAttributeList()

    # First set up different data for each item
    for x in range(arbitrary_list_len):
        my_list.append(jgt_common.ResponseInfo(data=x))

    my_list.update_all(data=random_string, data2=random_string + random_string)

    # make sure new values are consisten across each element.
    assert my_list.data == [random_string] * arbitrary_list_len
    assert my_list.data2 == [random_string + random_string] * arbitrary_list_len


def test_responselist_set():
    arbitrary_list_len = random.randint(1, 10)  # Anything > 0 is fine.
    my_list = jgt_common.ResponseList()
    my_list.extend(range(arbitrary_list_len))
    assert len(my_list) == arbitrary_list_len
    my_list.set([])
    assert len(my_list) == 0
    my_list.set([-1, -2])
    assert len(my_list) == 2
    assert my_list == [-1, -2]


def test_responselist_single_item():
    my_list = jgt_common.ResponseList()
    with pytest.raises(AssertionError):
        my_list.single_item

    my_list.append(3)
    assert my_list.single_item == 3

    my_list.append(4)
    with pytest.raises(AssertionError):
        my_list.single_item


def test_response_list_build_and_set(random_string):
    response_list = jgt_common.ResponseList()

    assert len(response_list) == 0
    response_list.build_and_set(response=random_string)
    assert len(response_list) == 1
    assert isinstance(response_list.single_item, jgt_common.ResponseInfo)


def test_response_list_run_response_callbacks():
    arbitrary_list_len = random.randint(1, 10)  # Anything > 0 is fine.
    response_list = jgt_common.ResponseList()

    response_list.extend(
        jgt_common.ResponseInfo(response_callback=arbitrary_callback)
        for x in range(arbitrary_list_len)
    )
    arbitrary_callback_counter[0] = 0
    response_list.run_response_callbacks()
    assert arbitrary_callback_counter[0] == arbitrary_list_len


TICKET_DATA = (
    ("XYZZY-1234", "JIRA"),
    ("XYZZY1234", "SNOW"),
    ("XY1", "SNOW"),
    ("X-2345", "VersionOne"),
    ("XY-2345", "JIRA"),
    ("1234", ""),
    ("A123", ""),
    ("XY", ""),
    ("XY-F123", ""),
    ("XY-FOOBAR", ""),
    ("", ""),
)


@pytest.mark.parametrize("ticket_id,system", TICKET_DATA)
def test_ticketing_system_identification(ticket_id, system):
    assert jgt_common.ticketing_system_for(ticket_id) == system


@pytest.mark.parametrize("ticket_id,system", TICKET_DATA)
def test_ticketing_system_urls(ticket_id, system):
    url = jgt_common.url_if_ticket(ticket_id)
    if system and system not in jgt_common.OBSOLETE_TICKETING_SYSTEMS:
        assert ticket_id in url
    else:
        assert url == ""


UUID_BASIC_MATCHER = re.compile(jgt_common.UUID_BASIC_RE)


def uuids_with_extra_text():
    target_uuid = str(uuid4())
    extra_text = jgt_common.generate_random_string()
    return [
        extra_text + target_uuid,
        extra_text + target_uuid + extra_text,
        target_uuid + extra_text,
    ]


def broken_uuids():
    target_uuid = str(uuid4())
    return [
        target_uuid[1:],
        target_uuid[:-1],
        target_uuid.replace("-", ""),
        target_uuid.replace("-", "+"),
    ]


def test_solo_uuid_basic_positive():
    uuid_value = str(uuid4())
    assert len(UUID_BASIC_MATCHER.findall(uuid_value)) == 1


@pytest.mark.parametrize("uuid_with_extra_text", uuids_with_extra_text())
def test_uuid_basic_positive(uuid_with_extra_text):
    assert len(UUID_BASIC_MATCHER.findall(uuid_with_extra_text)) == 1


@pytest.mark.parametrize("broken_uuid", broken_uuids())
def test_uuid_basic_negative(broken_uuid):
    assert len(UUID_BASIC_MATCHER.findall(broken_uuid)) == 0


UUID_ISOLATED_MATCHER = re.compile(jgt_common.UUID_ISOLATED_RE)


def uuids_with_isolated_extra_text():
    target_uuid = str(uuid4())
    extra_text = jgt_common.generate_random_string()
    return [
        target_uuid,
        "/" + target_uuid,
        extra_text + "-" + target_uuid + "-",
        target_uuid + "/" + extra_text,
    ]


def test_solo_uuid_isolated_positive():
    uuid_value = str(uuid4())
    assert len(UUID_ISOLATED_MATCHER.findall(uuid_value)) == 1


@pytest.mark.parametrize(
    "uuid_with_isolated_extra_text", uuids_with_isolated_extra_text()
)
def test_uuid_isolated_positive(uuid_with_isolated_extra_text):
    assert len(UUID_ISOLATED_MATCHER.findall(uuid_with_isolated_extra_text)) == 1


@pytest.mark.parametrize("uuid_with_extra_text", uuids_with_extra_text())
def test_uuid_isolated_negative(uuid_with_extra_text):
    assert len(UUID_ISOLATED_MATCHER.findall(uuid_with_extra_text)) == 0


@pytest.mark.parametrize("bad_arg", ["4", object(), None])
def test_percent_diff_bad_input(bad_arg):
    with pytest.raises(TypeError):
        assert jgt_common.percent_diff(bad_arg, 1) == 1.0


@pytest.mark.parametrize(
    "precision,expected",
    [(1, 15.1), (2, 15.05), (3, 15.051), (4, 15.0513), (5, 15.05132)],
)
def test_percent_diff(precision, expected):
    assert jgt_common.percent_diff(21.443, 25.2423, precision) == expected


def test_percent_diff_no_diff():
    assert jgt_common.percent_diff(1, 1) == 0.0


def test_percent_diff_zero_arg():
    assert jgt_common.percent_diff(0, 1) is nan


@pytest.mark.parametrize(
    "value,name",
    [
        (True, "I am True"),
        (False, "False is my value"),
        (1, "1 is not False"),  # Arbitrary truthy value '1'
        ("", "Empty string is not True"),  # Arbitrary falsey value ""
    ],
)
def test_flag_basics(value, name):
    flag = jgt_common.Flag(initial_value=value, name=name)
    original_bool_ness = bool(value)
    assert bool(flag) is original_bool_ness
    assert flag.value is bool(value)
    assert flag.name == name

    # Now see if toggle returns the original value...
    assert flag.toggle() is original_bool_ness
    # and sets the current value to it's opposite
    assert bool(flag) is not original_bool_ness


def test_accumulator_for():
    def helper():
        return "Arbitrary value"

    helper_a = jgt_common.accumulator_for(helper)
    helper_b = jgt_common.accumulator_for(helper)

    # arbitrary values, but they should be different:
    call_a_count = 5
    call_b_count = call_a_count + 3

    for x in range(call_a_count):
        a_list = helper_a()

    for x in range(call_b_count):
        b_list = helper_b()

    assert a_list is not b_list, "Accumulators should be different lists"
    assert len(a_list) != len(b_list), "Accumulators mixed up"
    assert len(a_list) == call_a_count, "Accumulator failure for a"
    assert len(b_list) == call_b_count, "Accumulator failure for b"


def test_assert_if_values():
    @jgt_common.assert_if_values("Got some odd values:\n{}")
    def assert_all_odd_values(sequence):
        for item in sequence:
            if item % 2:
                yield f"{item} is odd!"

    with pytest.raises(AssertionError):
        # Pick an arbitrary range size, long enough to have some odd values in it
        assert_all_odd_values(range(10))

    # a few arbitrary non-odd values:
    assert_all_odd_values([0, 2, 100, 200])

    # No values, no problem.
    assert_all_odd_values([])
