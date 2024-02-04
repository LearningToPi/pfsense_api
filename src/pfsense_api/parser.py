'''
The file provides utility functions for parsing and handling data, 
particularly focused on processing HTML tables, JSON, and specific 
data formats like HAProxy JSON. It defines various classes and 
functions, including parsers for different data types.

MIT License

Copyright (c) 2023 LearningToPi

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

'''

from collections import namedtuple
import re
import json
from datetime import datetime
from logging_handler import create_logger, INFO
from lxml import etree


DEFAULT_LOGGING = INFO
DEFAULT_TYPEFIX = True


def var_name_clean(var_name:str) -> str:
    '''Clean a variable name to remove invalid names.

    Args:
        var_name (str): The input variable name.

    Returns:
        str: Cleaned variable name.
    '''
    if var_name is None:
        return ''
    if len(var_name) == 0:
        raise ValueError("var_name_clean: Var name is empty!")
    if not isinstance(var_name, str):
        var_name = str(var_name)
    if var_name[0].isdigit():
        var_name = 'd' + var_name
    if var_name[0] == '_':
        var_name = 'd' + var_name
    for invalid_char in re.finditer(r'[^A-Za-z0-9_]', var_name):
        var_name = var_name[0:invalid_char.span()[0]] + '_' + var_name[invalid_char.span()[1]:]
    return var_name.lower()


def header_dedup(headers:list) -> list:
    '''Rename duplicate headers to prevent issues with namedtuples conversion.

    Args:
        headers (list): List of headers.

    Returns:
        list: Deduplicated headers.
    '''
    header_dict = {}
    for header in headers:
        if header not in header_dict:
            header_dict[header] = 0
        else:
            header_dict[header] += 1
            header_dict[f"{header}_{header_dict[header]}"] = 0
    return list(header_dict.keys())


def update_type(data:str|dict|list|None):
    '''Format data as bool, int, float, etc. Convert datetime and size formats.

    Args:
        data (str | dict | list | None): Input data.

    Returns:
        Formatted data based on type.
    '''
    if isinstance(data, str):
        if data.isnumeric():
            return int(data)
        if data.replace('.','', 1).isnumeric():
            return float(data)
        if data.lower() == 'true':
            return True
        if data.lower() == 'false':
            return False
        date_formats = ['%a %b %d %H:%M:%S %Z %Y', '%a %b %d %H:%M:%S %Y', '%Y-%m-%d %H:%M:%S']
        for date_format in date_formats:
            try:
                # format for general
                return datetime.strptime(data, date_format)
            except: # pylint: disable=W0702
                pass
        size_re = re.search(r'^(?P<value>[0-9.]*)\s*(?P<unit>([Tt][Ii][Bb])|([Gg][Ii][Bb])|([Mm][Ii][Bb])|([Kk][Ii][Bb])|G|M|T|K)$', data)
        if size_re:
            if size_re.groupdict()['unit'].lower() == 'kib' or size_re.groupdict()['unit'] == 'K':
                return float(size_re.groupdict()['value']) * 1024
            if size_re.groupdict()['unit'].lower() == 'mib' or size_re.groupdict()['unit'] == 'M':
                return float(size_re.groupdict()['value']) * 1024 * 1024
            if size_re.groupdict()['unit'].lower() == 'gib' or size_re.groupdict()['unit'] == 'G':
                return float(size_re.groupdict()['value']) * 1024 * 1024 * 1024
            if size_re.groupdict()['unit'].lower() == 'tib' or size_re.groupdict()['unit'] == 'T':
                return float(size_re.groupdict()['value']) * 1024 * 1024 * 1024 * 1024
        # return as is
        return data
    if data is None:
        return None
    if isinstance(data, list):
        new_data = []
        for entry in data:
            new_data.append(update_type(entry))
        return new_data
    if isinstance(data, dict):
        new_data = {}
        for item, value in data.items():
            new_data[item] = update_type(value)
        return new_data
    if isinstance(data, tuple):
        # leave tuples alone as they are immutable and we don't want to change named tuples
        return data
    raise ValueError(f"Data of type {type(data)} is not supported. Pass string, dict or list")


def html_text(col:etree.ElementBase) -> str:
    '''Return the combined text from the HTML field.

    Args:
        col (etree.ElementBase): HTML element.

    Returns:
        str: Combined text from the HTML field.
    '''
    return ' ' + str(col.text or '').strip() + ' '.join([html_text(x) for x in col.getchildren()]) + str(col.tail or '').strip()


class ContentParser:
    '''Base parser for different parser types.

    Attributes:
        _logger: Logger instance for the parser.
        type_fix (bool): Flag to enable type fixing in parsing.
    '''
    def __init__(self, log_level:str=DEFAULT_LOGGING, type_fix:bool=DEFAULT_TYPEFIX):
        self._logger = create_logger(log_level, name=__class__.__name__)
        self.type_fix = type_fix

    def parse(self, *args) -> object:
        ''' Return the first arg back. Used as a placeholder '''
        return args[0] if len(args) > 0 else None


class ContentParserRegex(ContentParser):
    '''Parser to handle strings.

    Attributes:
        regex (str): Regular expression pattern for parsing.
        find_all (bool): Flag to indicate if findall should be used.
    '''
    def __init__(self, regex:str, log_level:str=DEFAULT_LOGGING, find_all:bool=False, type_fix:bool=DEFAULT_TYPEFIX):
        super().__init__(log_level=log_level, type_fix=type_fix)
        self.regex = regex
        self.find_all = find_all

    def parse(self, content) -> tuple|list[tuple]:
        ''' Parse the supplied content.  If find_all, then runs regex findall and iterates through creating a list to return, otherwise returns a dict'''
        self._logger.debug(f"Running parse using regex: {self.regex}...")
        if self.find_all:
            return_data = []
            re_finditer = re.finditer(self.regex, str(content))
            if not re_finditer:
                return []
            for re_instance in re_finditer:
                self._logger.debug(f"Found instance (findall): {re_instance}")
                tuple_instance = namedtuple(self.__class__.__name__, (re_instance.groupdict().keys()))
                data_tuple = tuple_instance(**(update_type(re_instance.groupdict()) if self.type_fix else re_instance.groupdict())) # type: ignore
                self._logger.debug(f"Parsed data: {data_tuple}")
                return_data.append(data_tuple)
            return return_data
        else:
            re_search = re.search(self.regex, str(content))
            if not re_search:
                return tuple()
            self._logger.debug(f"Found instance: {re_search}")
            tuple_instance = namedtuple(self.__class__.__name__, (re_search.groupdict().keys()))
            data_tuple = tuple_instance(**(update_type(re_search.groupdict()) if self.type_fix else re_search.groupdict())) # type: ignore
            self._logger.debug(f"Parsed data: {data_tuple}")
            return data_tuple


class ContentParserJson(ContentParser):
    '''Parser to handle JSON data and return in the named tuple format.

    Attributes:
        None
    '''
    def __init__(self, log_level:str=DEFAULT_LOGGING, type_fix:bool=DEFAULT_TYPEFIX):
        super().__init__(log_level=log_level,type_fix=type_fix)

    def parse(self, content:str|dict|list) -> tuple|list[tuple]:
        ''' Parse the supplied text or dict or list and return as a named tuple '''
        if isinstance(content, str):
            json_content = json.loads(content)
        else:
            json_content = content
        return_data = []
        self._logger.debug(f"Parsing content as json: {json_content}...")
        # if we are not a list, convert to a single item list so we can write the logic once
        for record in json_content if isinstance(json_content, list) else [json_content]:
            if isinstance(record, dict):
                tuple_instance = namedtuple(self.__class__.__name__, (record.keys()))
                return_data.append(tuple_instance(**(update_type(record) if self.type_fix else record))) # type: ignore
        if isinstance(content, dict):
            return return_data[0] if len(return_data) > 0 else tuple()
        return return_data


class ContentParserHtmlTable(ContentParser):
    '''Parses an HTML table using either the top row or first column as the index.

    Attributes:
        headers (str): LXML format for the tags to find the header field.
        records (str): LXML format for the tags to find the list of records.
        index_top (bool): Use the top as the index, otherwise swap.
        record_parser (dict): Dictionary of record parsers.
        split_string (str | None): String to use to split multiple tables.
    '''
    def __init__(self, headers:str, records:str, index_top=True, record_regex:dict|None=None, record_regex_findall:bool=False,
                 split_string:str|None=None, header_regex:str|None=None, split_range:tuple|None=None,
                 log_level:str=DEFAULT_LOGGING, type_fix:bool=DEFAULT_TYPEFIX):
        ''' 
        Parses an HTML table using either the top row or first column as the only index

        parameters:
            headers - lxml format for the tags to find the header field for the table
            records - lxml format for the tags to find the list of records in the table
            index_top (bool) - Use the top as the "index" and first for as field name. Otherwise swap
            record_regex (dict) - if we need to run a regex against the record, provide it here, using a dict to specify field and regex string
            record_regex_findall (bool) - Pass through flag for the regex parser
            split_string (str) - String to use to split multiple tables
            header_regex (str) - Regex to use to pull the title for the table
             split_range (tuple) - Tuple of 1 or 2 values. Use as list slicing, 1st value is start, 2nd value is end (-1 ok) '''
        super().__init__(log_level=log_level, type_fix=type_fix)
        self.headers, self.records, self.index_top, self.split_string, self.header_regex, self.split_range = headers, records, index_top, split_string, header_regex, split_range
        self.record_parser = {}
        if record_regex:
            for item, value in record_regex.items():
                self.record_parser[item] = ContentParserRegex(regex=value, find_all=record_regex_findall)

    def parse(self, content:str) -> dict|list:
        ''' Parse the supplied HTML and return a dict of named tuples '''
        tables = []
        table_num = 0
        # if we have multiple tables on a page, split it out
        for table_content in content.split(self.split_string) if self.split_string is not None else [content]:
            table_title = table_num
            if self.header_regex is not None:
                table_header_re = re.search(self.header_regex, table_content)
                if table_header_re:
                    table_title = table_header_re.groups()[0]
            records = []
            col_tree = etree.HTML(str(table_content)).find(self.headers) # type: ignore
            col_headers = header_dedup([var_name_clean(x.text) for x in col_tree if not isinstance(x, etree._Comment)] if col_tree is not None else [])
            self._logger.debug(f"Parsing HTML table, header row: {col_headers}")
            row_tree = etree.HTML(str(table_content)).find(self.records) # type: ignore
            for row in row_tree if row_tree is not None else []:
                fields = [html_text(col).strip() for col in row.getchildren()]
                #fields = [col.text.strip() if col.text is not None and col.text.strip() != '' else '' + ''.join([x.text for x in col.getchildren() if x.text is not None]) for col in row.getchildren()]
                self._logger.debug(f"Parsing HTML table, record row: {fields}")
                # format based on top or side index
                if self.index_top:
                    if len(fields) > 0:
                        # pass the data through a content parser if one has been provided, otherwise use the default contentparser
                        records.append({col_headers[x]:self.record_parser.get(col_headers[x], ContentParser()).parse(fields[x]) for x in range(len(col_headers)) if x < len(fields)})
                else:
                    raise NotImplementedError("HTML Table index column not yet implemented.")
            # remove invalid headers ('')
            fixed_col_headers = [x for x in col_headers if x != '']
            # convert to a namedtuple and return)
            if self.index_top:
                tuple_row = namedtuple(self.__class__.__name__ + '_row', fixed_col_headers)
            else:
                raise NotImplementedError("HTML Table index column not yet implemented.")
            temp_data = []
            for record in records:
                # need to drop any columns from the records that are 
                temp_data.append(tuple_row(**(update_type({item:value for item, value in record.items() if item in fixed_col_headers}) if self.type_fix else {item:value for item, value in record.items() if item in fixed_col_headers}))) # type: ignore
            tables.append({table_title: temp_data})

        if self.split_string is None and len(tables) > 0:
            # we have a single table, so no need to return a dict
            if self.header_regex is None:
                # we don't have a header, so just return the list
                return tables[0][0]
            return tables[0]

        # if a split range was provided, return that range
        if self.split_range is not None:
            return_list = tables[self.split_range[0]:self.split_range[1] if len(self.split_range) > 1 and self.split_range[1] > len(tables) else len(tables)]
            x = 0
            while x < len(return_list):
                # check for and remove any empty tables
                if 0 in return_list[x].keys() and return_list[x][0] == []:
                    return_list.pop(x)
                else:
                    x += 1
            # if we have only 1 item, don't return a dict, just return that table
            return {key: item for x in return_list for key, item in x.items()} if len(return_list) > 1 else return_list[0][list(return_list[0].keys())[0]]
        return {key: item for x in tables for key, item in x.items()}


class ContentParserHtmlMatrix(ContentParser):
    '''Parses an HTML table using dual indexes, either top row and first column or first column and top row.

    Attributes:
        headers (str): LXML format for the tags to find the header field.
        records (str): LXML format for the tags to find the list of records.
        index_top (bool): Use the top as the index, otherwise swap.
        record_parser (ContentParserRegex): Record parser for regex.
    '''
    def __init__(self, headers:str, records:str, index_top=True, record_regex:str|None=None, record_regex_findall:bool=False,
                 log_level:str=DEFAULT_LOGGING, type_fix:bool=DEFAULT_TYPEFIX):
        ''' 
        Parses an HTML table using dual indexes, either top row and first column or first column and top row.

        parameters:
            headers - lxml format for the tags to find the header field for the table
            records - lxml format for the tags to find the list of records in the table
            index_top (bool) - Use the top as the "index" and first for as field name. Otherwise swap
            record_regex (str) - if we need to run a regex against the record, provide it here
            record_regex_findall (bool) - Pass through flag for the regex parser '''
        super().__init__(log_level=log_level, type_fix=type_fix)
        self.headers, self.records, self.index_top, = headers, records, index_top
        if record_regex:
            self.record_parser = ContentParserRegex(regex=record_regex, find_all=record_regex_findall)
        else:
            # use a base parsers that just passes through to simplify code
            self.record_parser = ContentParser()

    def parse(self, content:str) -> tuple:
        ''' Parse the supplied HTML. Return a list of tuples '''
        table_data = {}
        col_headers = header_dedup([var_name_clean(x.text) for x in etree.HTML(str(content)).find(self.headers)]) # type: ignore
        row_headers = []
        self._logger.debug(f"Parsing HTML table, header row: {col_headers}")
        for row in etree.HTML(str(content)).find(self.records): # type: ignore
            fields = [col.text if col.text is not None else '' + ''.join([x.text for x in col.getchildren() if x.text is not None]) for col in row.getchildren()]
            row_headers.append(fields[0])
            self._logger.debug(f"Parsing HTML table, record row: {fields}")
            # Format based on top or side index
            if self.index_top:
                for x in range(1, len(col_headers)):
                    if col_headers[x] not in table_data:
                        table_data[col_headers[x]] = {}
                    table_data[var_name_clean(col_headers[x])][var_name_clean(fields[0])] = self.record_parser.parse(fields[x])
            else:
                for x in range(1, len(fields)):
                    if fields[0] not in table_data:
                        table_data[fields[0]] = {}
                    table_data[var_name_clean(fields[0])][var_name_clean(col_headers[x])] = self.record_parser.parse(fields[x])
        # convert to a namedtuple and return)
        if self.index_top:
            tuple_row = namedtuple(self.__class__.__name__ + '_row', [var_name_clean(x) for x in row_headers])
            tuple_index = namedtuple(self.__class__.__name__ + '_index', [var_name_clean(x) for x in col_headers[1:]])
        else:
            tuple_row = namedtuple(self.__class__.__name__, [var_name_clean(x) for x in col_headers[1:]])
            tuple_index = namedtuple(self.__class__.__name__ + '_index', [var_name_clean(x) for x in row_headers])
        temp_data = {}
        for key, value in table_data.items():
            temp_data[key] = tuple_row(**(update_type(value) if self.type_fix else value)) # type: ignore
        return tuple_index(**temp_data)
        #return tuple_index(**(update_type(temp_data) if self.type_fix else temp_data)) # type: ignore


class ContentParserHaProxy(ContentParser):
    '''Parser to handle HAProxy JSON data and return in the named tuple format.

    Attributes:
        None
    '''
    def __init__(self, log_level:str=DEFAULT_LOGGING, type_fix:bool=DEFAULT_TYPEFIX):
        super().__init__(log_level=log_level,type_fix=type_fix)

    def parse(self, content:str|dict|list) -> dict:
        ''' Parse the supplied text or dict or list and return as a named tuple '''
        json_content = json.loads(content) if isinstance(content, str) else content
        self._logger.debug(f"Parsing content as HA PROXY json: {json_content}...")
        # HA proxy returns json in an odd format
        # list - List of objects ()
        #   list - List of properties for the object
        #       objType (str) - Frontend, Backend, Server - Present for all properties
        #       proxyId (int) - ID for something.  Servers in the same group have the same ID
        #       id (int) - Another ID, 0 for everything except servers which have a unique ID
        #       field (dict) -
        #           pos (int) - order of the properties?  seems useless
        #           name (str) - Name of the property!!
        #       processNum (int) - I believe this is a HA proxy process number, all of mine are 1
        #       tags (dict) - "origin", "nature", "scope", all string values
        #       value (dict) -
        #           type (str) - What is the format fo the value (str, u32, u64, etc)
        #           value (varies) - Actual value!

        # loop through list list of objects
        ha_proxy = {}
        for pxy_obj in json_content:
            tmp_props = {}
            # loop through the properties and detangle the mess
            tmp_props['objType'] = pxy_obj[0]['objType']
            tmp_props['proxyId'] = pxy_obj[0]['proxyId']
            tmp_props['id'] = pxy_obj[0]['id']
            tmp_props['processNum'] = pxy_obj[0]['processNum']
            for pxy_prop in pxy_obj:
                if 'field' in pxy_prop and 'value' in pxy_prop:
                    tmp_props[pxy_prop['field']['name']] = {'value': pxy_prop['value']['value'], 'tags': pxy_prop['tags'] if 'tags' in pxy_prop else None}
            # pull out the pxname and svname from the prop list to use as key values
            pxname = tmp_props['pxname']['value']
            svname = tmp_props['svname']['value']
            tmp_props.pop('pxname')
            tmp_props.pop('svname')
            # add the pxname and svname to the ha_proxy table with the associated properties
            if pxname not in ha_proxy:
                ha_proxy[pxname] = {}
            ha_proxy[pxname][svname] = tmp_props
        return ha_proxy
