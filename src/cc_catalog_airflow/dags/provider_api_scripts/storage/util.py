"""
This module has a number of public methods which are useful for storage
operations.
"""
import json
import logging
from urllib.parse import urlparse

from storage import constants

logger = logging.getLogger(__name__)

LICENSE_PATH_MAP = constants.LICENSE_PATH_MAP


def choose_license_and_version(
        license_url=None, license_=None, license_version=None
):
    derived_license, derived_version = _get_license_from_url(license_url)
    if derived_license and derived_version:
        # We prefer license and version derived from the license_url, when
        # possible, since we have more control over the string
        # (capitalization, etc.)
        logger.debug(
            'Using derived_license {} and derived_version {}'
            .format(derived_license, derived_version)
        )
        license_, license_version = derived_license, derived_version
    else:
        logger.debug(
            'Using given license_ {} and license_version {}'
            .format(license_, license_version)
        )

    return _validate_license_pair(license_, license_version)


def validate_url_string(url_string):
    parse_result = urlparse(url_string)
    if type(url_string) == str and parse_result.scheme and parse_result.netloc:
        return url_string
    else:
        logger.debug('No valid url found in {}'.format(url_string))
        return None


def ensure_int(unknown_input):
    try:
        number = int(float(unknown_input))
    except Exception as e:
        logger.warning(
            'input {} is not castable to an int.  The error was {}'
            .format(unknown_input, e)
        )
        number = None
    return number


def ensure_sql_bool(bool_str, default=None):
    if bool_str in ['t', 'f']:
        return bool_str
    else:
        logger.warning('{} is not a valid PostgreSQL bool'.format(bool_str))
        return default


def enforce_char_limit(string, limit, truncate=True):
    if not type(string) == str:
        logger.warning(
            'Cannot limit characters on non-string type {}.  Input was {}.'
            .format(type(string), string)
        )
        return None
    if len(string) > limit:
        logger.warning(
            'String over char limit of {}.  Input was {}.'
            .format(limit, string)
        )
        return string[:limit] if truncate else None
    else:
        return string


def get_provider_and_source(provider, source, default=None):
    if not provider:
        provider = default
    if not source:
        source = provider

    return provider, source


def enforce_all_arguments_truthy(**kwargs):
    all_truthy = True
    for arg in kwargs:
        if not kwargs[arg]:
            logging.warning('Missing {}'.format(arg))
            all_truthy = False
    return all_truthy


def prepare_output_field_string(unknown_input):
    if not unknown_input:
        return '\\N'
    elif type(unknown_input) in [dict, list]:
        return json.dumps(_sanitize_json_values(unknown_input))
    else:
        return _sanitize_string(unknown_input)


def _sanitize_json_values(unknown_input, recursion_limit=100):
    """
    Recursively sanitizes the non-dict, non-list values of an input
    dictionary or list in preparation for dumping to JSON string.
    """
    input_type = type(unknown_input)
    if input_type not in [dict, list] or recursion_limit <= 0:
        return _sanitize_string(unknown_input)
    elif input_type == list:
        return [
            _sanitize_json_values(
                item,
                recursion_limit=recursion_limit - 1
            )
            for item in unknown_input
        ]
    else:
        return {
            key: _sanitize_json_values(
                val,
                recursion_limit=recursion_limit - 1
            )
            for key, val in unknown_input.items()
        }


def _sanitize_string(data):
    if data is None:
        return ''
    else:
        # We join a split string because it removes all whitespace
        # characters
        return ' '.join(
            str(data)
            .replace('"', "'")
            .replace('\b', '')
            .replace('\\', '\\\\')
            .split()
        )


def _get_license_from_url(license_url, path_map=LICENSE_PATH_MAP):
    license_url = validate_url_string(license_url)
    if license_url:
        parsed_license_url = urlparse(license_url)
    else:
        return None, None

    license_, license_version = None, None
    if parsed_license_url.netloc != 'creativecommons.org':
        logger.warning(
            'The license at {} is not issued by Creative Commons.'
            .format(license_url)
        )
    else:
        for valid_path in path_map:
            if valid_path in parsed_license_url.path.lower():
                license_ = path_map[valid_path]['license']
                license_version = path_map[valid_path]['version']

                logger.debug(
                    'Derived license_: {}, Derived license_version: {}'
                    .format(license_, license_version)
                )

    return license_, license_version


def _validate_license_pair(
        license_,
        license_version,
        path_map=LICENSE_PATH_MAP
):
    pairs = ((item['license'], item['version']) for item in path_map.values())
    if (license_, license_version) not in pairs:
        logger.warning(
            '{}, {} is not a valid license, license_version pair'
            .format(license_, license_version)
        )
        license_, license_version = None, None
    return license_, license_version
