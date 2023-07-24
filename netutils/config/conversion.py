"""Configuration conversion methods for different network operating systems."""

import typing as t
import xml.etree.ElementTree as ET


from netutils.config.utils import _open_file_config

conversion_map: t.Dict[str, t.List[str]] = {
    "paloalto_panos": ["paloalto_panos_brace_to_set"],
    "calix_calixos": ["calix_calixos_xml_to_cli"],
}


def paloalto_panos_brace_to_set(cfg: str, cfg_type: str = "file") -> str:
    r"""Convert Palo Alto Brace format configuration to set format.

    Args:
        cfg: Configuration as a string
        cfg_type: A string that is effectively a choice between `file` and `string`. Defaults to `file`.

    Returns:
        str: Converted configuration as a string.

    Examples:
            >>> config = '''
            ...     config {
            ...            mgt-config {
            ...                users {
            ...                  admin {
            ...                    phash *;
            ...                    permissions {
            ...                      role-based {
            ...                        superuser yes;
            ...                      }
            ...                    }
            ...                    public-key thisisasuperduperlongbase64encodedstring;
            ...                }
            ...                panadmin {
            ...                    permissions {
            ...                      role-based {
            ...                        superuser yes;
            ...                      }
            ...                    }
            ...                    phash passwordhash;
            ...                }
            ...              }
            ...            }
            ...         }'''
            >>> paloalto_panos_brace_to_set(cfg=config, cfg_type='string') == \
            ... '''set mgt-config users admin phash *
            ... set mgt-config users admin permissions role-based superuser yes
            ... set mgt-config users admin public-key thisisasuperduperlongbase64encodedstring
            ... set mgt-config users panadmin permissions role-based superuser yes
            ... set mgt-config users panadmin phash passwordhash'''
            True
    """
    stack: t.List[str] = []
    cfg_value: t.List[str] = []
    cfg_string: str = ""

    if cfg_type not in ["file", "string"]:
        raise ValueError("The variable `cfg_type` must be either `file` or `string`.")
    if cfg_type == "file":
        cfg_list = _open_file_config(cfg).splitlines()
    else:
        cfg_list = cfg.splitlines()

    for i, line in enumerate(cfg_list):
        line = line.strip()
        if line.endswith(";") and not line.endswith('";'):
            line = line.split(";", 1)[0]
            line = "".join(str(s) for s in stack) + line
            line = line.split("config ", 1)[1]
            line = "set " + line
            cfg_value.append(line.strip())
        elif line.endswith('login-banner "') or line.endswith('content "'):
            _first_banner_line = "".join(str(s) for s in stack) + line
            cfg_value.append("set " + _first_banner_line.split("config ", 1)[1])

            for banner_line in cfg_list[i + 1:]:  # fmt: skip
                if '"' in banner_line:
                    banner_line = banner_line.split(";", 1)[0]
                    cfg_value.append(banner_line.strip())
                    break
                cfg_value.append(banner_line.strip())
        elif line.endswith("{"):
            stack.append(line[:-1])
        elif line == "}" and len(stack) > 0:
            stack.pop()

    for _l, _line in enumerate(cfg_value):
        cfg_string += _line
        if _l < len(cfg_value) - 1:
            cfg_string += "\n"

    return cfg_string


def calix_calixos_xml_to_cli(cfg: str, cfg_type: str = "file") -> str:
    r"""Convert Calix XML Configuration to CLI Format.

    Args:
        cfg: Configuration as a string
        cfg_type: A string that is effectively a choice between `file` and `string`. Defaults to `file`.

    Returns:
        str: Converted configuration as a string.

    Examples:
    >>> config = '''
    ...     <config>
    ...         <interface>
    ...             <gigabitethernet>
    ...             <name>1/1/1</name>
    ...             <description>Example interface</description>
    ...             <ip>
    ...                 <address>
    ...                 <ip-address>192.168.1.10</ip-address>
    ...                 <subnet-mask>255.255.255.0</subnet-mask>
    ...                 </address>
    ...             </ip>
    ...             <shutdown>false</shutdown>
    ...             </gigabitethernet>
    ...         </interface>
    ...      </config>'''
    >>> calix_calixos_xml_to_cli(cfg=config, cfg_type='string') == \
    ... '''interface
    ...   gigabitethernet
    ...     name 1/1/1
    ...     description Example interface
    ...     ip
    ...       address
    ...         ip-address 192.168.1.10
    ...         subnet-mask 255.255.255.0
    ...     shutdown false'''
    True
    """
    cli_config: str = ""

    if cfg_type not in ["file", "string"]:
        raise ValueError("The variable `cfg_type` must be either `file` or `string`.")
    if cfg_type == "file":
        xml_config = _open_file_config(cfg)
    else:
        xml_config = cfg

    def parse_element(element, indent):
        lines = []
        tag_name = element.tag
        text = element.text.strip() if element.text else ""

        if tag_name == "config":
            pass
        elif tag_name == "exit":
            lines.append(indent[:-2] + "exit")
        elif tag_name == "no":
            lines.append(indent[:-2] + "no " + text)
        else:
            lines.append(indent[:-2] + tag_name + (" " + text if text else ""))

        for child in element:
            child_lines = parse_element(child, indent + "  ")
            lines.extend(child_lines)

        return lines

    try:
        xml_root = ET.fromstring(xml_config)
    except ET.ParseError as parse_error:
        print("Error parsing XML configuration:", str(parse_error))
        return ""

    config_element = ET.Element("config")
    config_element.extend(xml_root)

    cli_lines = parse_element(config_element, "")
    cli_config = "\n".join(cli_lines)
    return cli_config
