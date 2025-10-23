'''
Definition of the supported API calls.
Format:
{
    [name] (dict) - Name for the grouping
        request (dict) - define the request requirements
            path (str) - URL path to query (exclude host)
            method (str) - post/get
            data (dict) - Any data items to be sent with a post (__csrf_magic can be excluded)
            headers (dict) - Any header values to set with the post/get
            parameters (dict) - Any request parameters to add to the url string
        parser (ContentParser) - What parser to use for the returned data. Parser will define variables
}
'''
from .parser import ContentParserJson, ContentParserRegex, ContentParserHtmlMatrix, ContentParserHtmlTable, ContentParserHaProxy



SUPPORTED_READ_API =  {
    'general': {
        'request': {
            'path': 'getstats.php',
            'method': 'post',
            'data': {'skipitems[0]': ''}
        },
        'parser': ContentParserRegex(r'(?P<cpu_tick_total>[0-9]*)?[^|]*[|]'
                                     r'(?P<cpu_tick_used>[0-9]*)?[^|]*[|]'
                                     r'(?P<memory_used_percent>[0-9.]*)?[^|]*[|]'
                                     r'(?P<uptime_days>[0-9]*)?\s*(?:[Dd]ays)?\s*(?P<uptime_hours>[0-9]*)?\s*(?:[Hh]ours)?\s*(?P<uptime_minutes>[0-9]*)?\s*(?:[Mm]inutes)?\s*(?P<uptime_seconds>[0-9]*)?\s*(?:[Ss]econds)?\s*[^|]*[|]'
                                     r'(?P<state_used>[0-9]*)?\s*(?:/)?\s*(?P<state_max>[0-9]*)?[^|]*[|]'
                                     r'(?P<temp_c>[0-9.]*)?[^|]*[|]'
                                     r'(?P<datetime>[^|]*)?[^|]*[|]'
                                     r'(?:[Cc]urrent\s*:)?\s*(?P<cpu_freq_current>[0-9.]*)?\s*(?:[Mm][Hh][Zz]\s*,\s*[Mm]ax\s*:)?\s*(?P<cpu_freq_max>[0-9.]*)?\s*(?:[Mm][Hh][Zz])?[^|]*[|]'
                                     r'(?P<sys_load_1>[0-9.]*)?\s*(?:,)?\s*(?P<sys_load_5>[0-9.]*)?\s*(?:,)?\s*(?P<sys_load_15>[0-9.]*)?[^|]*[|]'
                                     r'(?P<mbuf_current>[0-9]*)?(?:/)?(?P<mbuf_max>[0-9]*)?[^|]*[|]'
                                     r'(?P<mbuf_percent>[0-9.]*)?[^|]*[|]'
                                     r'(?P<state_percent>[0-9]*)?[^|]*',
                                     type_fix=True)
    },
    'software_system': {
        'request': {
            'path': 'pkg_mgr_install.php',
            'method': 'post',
            'data': {'getversion': 'yes'},
        },
        'parser': ContentParserJson()
    },
    'thermal': {
        'request': {
            'path': 'widgets/widgets/thermal_sensors.widget.php',
            'method': 'post',
            'data': {'getThermalSensorsData': '1'}
        },
        'parser': ContentParserRegex(r'(?P<sensor>[A-Za-z0-9._-]*)\s*:\s*(?P<temp_c>[0-9.]*)[Cc]', find_all=True, type_fix=True)
    },
    'disks': {
        'request': {
            'path': 'widgets/widgets/disks.widget.php',
            'method': 'post',
            'data': {'widgetkey': 'disks-0'}
        },
        'parser': ContentParserHtmlTable(headers='body/thead',
                                         records='body/tbody',
                                         type_fix=True,
                                         record_regex={
                                             'usage': r"^(?P<usage_percent>[0-9.]*)%[^\(]*\((?P<fs_type>[^\]]*)\)"
                                         })
    },
    'interface_stats': {
        'request': {
            'path': "widgets/widgets/interface_statistics.widget.php",
            'method': 'post',
            'data': {'widgetkey': 'interface_statistics-0'}
        },
        'parser': ContentParserHtmlMatrix(headers='body/thead/tr', records='body/tbody', type_fix=True)
    },
    'openvpn_connections': {
        'request': {
            'path': 'status_openvpn.php',
            'method': 'get'
        },
        'parser': ContentParserHtmlTable(headers='body/div/table/thead/tr', 
                                         records='body/div/table/tbody',
                                         split_string='<div class="panel panel-default">',
                                         header_regex=r'<h2 class="panel-title">([^</]*)(?:[^<]*)?</h2>',
                                         split_range=(1,))
    },
    'dhcp_leases': {
        'request': {
            'method': 'get',
            'path': 'status_dhcp_leases.php'
        },
        'parser': ContentParserHtmlTable(headers='body/div/table/thead/tr',
                                         records='body/div/table/tbody',
                                         split_string='<div class="panel panel-default"',
                                         header_regex=r'<div class="panel-heading"><h2 class="panel-title">([^<]*)</h2></div>',
                                         split_range=(1,))
    },
    'gateways': {
        'request': {
            'method': 'get',
            'path': 'status_gateways.php'
        },
        'parser': ContentParserHtmlTable(headers='body/div/table/thead/tr',
                                         records='body/div/table/tbody',
                                         split_string='<div class="panel-body">',
                                         split_range=(1,))
    },
    'routes_v4': {
        'request': {
            'method': 'post',
            'path': 'diag_routes.php',
            'data': {'limit': 1000, 'IPv4': True, 'filter': '', 'isAjax': 1}
        },
        'parser': ContentParserRegex(regex=r'(?P<net>default|[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}(/[0-9]*)?)\s+'
                                           r'(?P<gw>link#[0-9]*|[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3})\s+'
                                           r'(?P<flags>[a-zA-Z0-9]*)\s+'
                                           r'(?P<uses>[0-9]*)\s+'
                                           r'(?P<mtu>[0-9]*)\s+'
                                           r'(?P<interface>[a-zA-Z0-9_]*)\s*\n',
                                     find_all=True)
    },
    'routes_v6': {
        'request': {
            'method': 'post',
            'path': 'diag_routes.php',
            'data': {'limit': 1000, 'IPv6': False, 'filter': '', 'isAjax': 1}
        },
        'parser': ContentParserRegex(regex=r'(?P<net>default|[0-9a-fA-F:]*(%[a-zA-Z0-9_]*)?(/[0-9]*)?)\s+'
                                           r'(?P<gw>link#[0-9]*|[0-9a-fA-F:]*(%[a-zA-Z0-9_]*)?)\s+'
                                           r'(?P<flags>[a-zA-Z0-9]*)\s+'
                                           r'(?P<uses>[0-9]*)\s+'
                                           r'(?P<mtu>[0-9]*)\s+'
                                           r'(?P<interface>[a-zA-Z0-9_]*)\s*\n',
                                     find_all=True)
    },
    'carp': {
        'request': {
            'method': 'get',
            'path': 'status_carp.php'
        },
        'parser': ContentParserHtmlTable(split_string='<div class="panel panel-default">',
                                         headers='body/div/table/thead/tr',
                                         records='body/div/table/tbody',
                                         header_regex=r'<div\s+class="panel-heading">\s*<h2s+class="panel-title">\s*([^<]*)\s*</h2>\s*</div>',
                                         split_range=(2,2))
    },
    'arp': {
        'request': {
            'method': 'get',
            'path': 'diag_arp.php'
        },
        'parser': ContentParserHtmlTable(split_string='<div class="panel panel-default">',
                                         headers='body/div/div/table/thead/tr',
                                         records='body/div/div/table/tbody',
                                         split_range=(1,))
    },
    'ndp': {
        'request': {
            'method': 'get',
            'path': 'diag_ndp.php'
        },
        'parser': ContentParserHtmlTable(split_string='<div class="panel panel-default">',
                                         headers='body/div/div/table/thead/tr',
                                         records='body/div/div/table/tbody',
                                         split_range=(1,))
    },
    'states': {
        'request': {
            'method': 'get',
            'path': 'diag_dump_states.php'
        },
        'parser': ContentParserHtmlTable(split_string='<div class="panel panel-default">',
                                         headers='body/div/div/table/thead/tr',
                                         records='body/div/div/table/tbody',
                                         split_range=(1,))
    },
    'haproxy': {
        'request': {
            'method': 'get',
            'path': 'haproxy/haproxy_stats.php',
            'parameters': {
                'haproxystats': "1;json"
            }
        },
        'parser': ContentParserHaProxy()
    }
}
