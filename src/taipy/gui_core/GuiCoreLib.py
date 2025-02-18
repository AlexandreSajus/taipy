# Copyright 2023 Avaiga Private Limited
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
# an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.

import typing as t
from urllib.parse import urlencode

from dateutil import parser

import taipy as tp
from taipy.core import Cycle, Scenario
from taipy.core.notification import CoreEventConsumerBase, EventEntityType
from taipy.core.notification.event import Event
from taipy.core.notification.notifier import Notifier
from taipy.gui import Gui, State
from taipy.gui.extension import Element, ElementLibrary, ElementProperty, PropertyType
from taipy.gui.utils import _TaipyBase

from ..version import _get_version


class GuiCoreScenarioAdapter(_TaipyBase):
    __INNER_PROPS = ["name"]

    def get(self):
        data = super().get()
        if isinstance(data, Scenario):
            return [
                data.id,
                data.is_primary,
                data.config_id,
                data.creation_date,
                data.get_simple_label(),
                list(data.tags),
                [(k, v) for k, v in data.properties.items() if k not in GuiCoreScenarioAdapter.__INNER_PROPS],
                [(p.id, p.get_simple_label()) for p in data.pipelines.values()],
                list(data.properties.get("authorized_tags", set())),
            ]
        return data

    @staticmethod
    def get_hash():
        return _TaipyBase._HOLDER_PREFIX + "Sc"


class GuiCoreContext(CoreEventConsumerBase):
    __PROP_SCENARIO_ID = "id"
    __PROP_SCENARIO_CONFIG_ID = "config"
    __PROP_SCENARIO_DATE = "date"
    __PROP_SCENARIO_NAME = "name"
    __PROP_SCENARIO_PRIMARY = "primary"
    __PROP_SCENARIO_TAGS = "tags"
    __SCENARIO_PROPS = (__PROP_SCENARIO_CONFIG_ID, __PROP_SCENARIO_DATE, __PROP_SCENARIO_NAME)
    _CORE_CHANGED_NAME = "core_changed"
    _SCENARIO_SELECTOR_ERROR_VAR = "gui_core_sc_error"
    _SCENARIO_SELECTOR_ID_VAR = "gui_core_sc_id"
    _SCENARIO_VIZ_ERROR_VAR = "gui_core_sv_error"

    def __init__(self, gui: Gui) -> None:
        self.gui = gui
        self.cycles_scenarios: t.Optional[t.List[t.Union[Cycle, Scenario]]] = None
        self.scenario_configs: t.Optional[t.List[t.Tuple[str, str]]] = None
        # register to taipy core notification
        reg_id, reg_queue = Notifier.register()
        super().__init__(reg_id, reg_queue)
        self.start()

    def process_event(self, event: Event):
        if event.entity_type == EventEntityType.SCENARIO or event.entity_type == EventEntityType.CYCLE:
            self.cycles_scenarios = None
            self.gui.broadcast(GuiCoreContext._CORE_CHANGED_NAME, {"scenario": True})

    @staticmethod
    def scenario_adapter(data):
        if isinstance(data, Cycle):
            return (data.id, data.name, tp.get_scenarios(data), 0, False)
        elif isinstance(data, Scenario):
            return (data.id, data.name, None, 1, data.is_primary)
        return data

    def get_scenarios(self):
        if self.cycles_scenarios is None:
            self.cycles_scenarios = []
            for cycle, scenarios in tp.get_cycles_scenarios().items():
                if cycle is None:
                    self.cycles_scenarios.extend(scenarios)
                else:
                    self.cycles_scenarios.append(cycle)
        return self.cycles_scenarios

    def select_scenario(self, state: State, id: str, action: str, payload: t.Dict[str, str]):
        args = payload.get("args")
        if args is None or not isinstance(args, list) or len(args) == 0:
            return
        scenario_id = args[0]
        state.assign(GuiCoreContext._SCENARIO_SELECTOR_ID_VAR, scenario_id)

    def get_scenario_by_id(self, id: str) -> t.Optional[Scenario]:
        if not id:
            return None
        try:
            return tp.get(id)
        except Exception:
            return None

    def get_scenario_configs(self):
        if self.scenario_configs is None:
            configs = tp.Config.scenarios
            if isinstance(configs, dict):
                self.scenario_configs = [(id, f"{c.id}") for id, c in configs.items()]
        return self.scenario_configs

    def crud_scenario(self, state: State, id: str, action: str, payload: t.Dict[str, str]):
        args = payload.get("args")
        if (
            args is None
            or not isinstance(args, list)
            or len(args) < 3
            or not isinstance(args[0], bool)
            or not isinstance(args[1], bool)
            or not isinstance(args[2], dict)
        ):
            return
        update = args[0]
        delete = args[1]
        data = args[2]
        name = data.get(GuiCoreContext.__PROP_SCENARIO_NAME)
        scenario = None
        if update:
            scenario_id = data.get(GuiCoreContext.__PROP_SCENARIO_ID)
            if delete:
                try:
                    tp.delete(scenario_id)
                except Exception as e:
                    state.assign(GuiCoreContext._SCENARIO_SELECTOR_ERROR_VAR, f"Error deleting Scenario. {e}")
            else:
                scenario = tp.get(scenario_id)
        else:
            config_id = data.get(GuiCoreContext.__PROP_SCENARIO_CONFIG_ID)
            scenario_config = tp.Config.scenarios.get(config_id)
            if scenario_config is None:
                state.assign(GuiCoreContext._SCENARIO_SELECTOR_ERROR_VAR, f"Invalid configuration id ({config_id})")
                return
            date_str = data.get(GuiCoreContext.__PROP_SCENARIO_DATE)
            try:
                date = parser.parse(date_str) if isinstance(date_str, str) else None
            except Exception as e:
                state.assign(GuiCoreContext._SCENARIO_SELECTOR_ERROR_VAR, f"Invalid date ({date_str}).{e}")
                return
            try:
                scenario = tp.create_scenario(scenario_config, date, name)
            except Exception as e:
                state.assign(GuiCoreContext._SCENARIO_SELECTOR_ERROR_VAR, f"Error creating Scenario. {e}")
        if scenario:
            with scenario as sc:
                sc._properties[GuiCoreContext.__PROP_SCENARIO_NAME] = name
                if props := data.get("properties"):
                    try:
                        for prop in props:
                            key = prop.get("key")
                            if key and key not in GuiCoreContext.__SCENARIO_PROPS:
                                sc._properties[key] = prop.get("value")
                        state.assign(GuiCoreContext._SCENARIO_SELECTOR_ERROR_VAR, "")
                    except Exception as e:
                        state.assign(GuiCoreContext._SCENARIO_SELECTOR_ERROR_VAR, f"Error creating Scenario. {e}")

    def edit_scenario(self, state: State, id: str, action: str, payload: t.Dict[str, str]):
        args = payload.get("args")
        if args is None or not isinstance(args, list) or len(args) < 1 or not isinstance(args[0], dict):
            return
        data = args[0]
        scenario_id = data.get(GuiCoreContext.__PROP_SCENARIO_ID)
        scenario: Scenario = tp.get(scenario_id)
        if scenario:
            with scenario as sc:
                try:
                    if data.get(GuiCoreContext.__PROP_SCENARIO_PRIMARY, False):
                        tp.set_primary(sc)
                    sc.tags = {t for t in data.get(GuiCoreContext.__PROP_SCENARIO_TAGS, [])}
                    sc._properties[GuiCoreContext.__PROP_SCENARIO_NAME] = data.get(GuiCoreContext.__PROP_SCENARIO_NAME)
                    if props := data.get("properties"):
                        for prop in props:
                            key = prop.get("key")
                            if key and key not in GuiCoreContext.__SCENARIO_PROPS:
                                sc._properties[key] = prop.get("value")
                        state.assign(GuiCoreContext._SCENARIO_VIZ_ERROR_VAR, "")
                except Exception as e:
                    state.assign(GuiCoreContext._SCENARIO_VIZ_ERROR_VAR, f"Error updating Scenario. {e}")

    def broadcast_core_changed(self):
        self.gui.broadcast(GuiCoreContext._CORE_CHANGED_NAME, "")


class GuiCore(ElementLibrary):
    __LIB_NAME = "taipy_gui_core"
    __CTX_VAR_NAME = f"__{__LIB_NAME}_Ctx"

    __elts = {
        "scenario_selector": Element(
            "value",
            {
                "show_add_button": ElementProperty(PropertyType.dynamic_boolean, True),
                "display_cycles": ElementProperty(PropertyType.dynamic_boolean, True),
                "show_primary_flag": ElementProperty(PropertyType.dynamic_boolean, True),
                "value": ElementProperty(PropertyType.lov_value),
                "on_change": ElementProperty(PropertyType.function),
            },
            inner_properties={
                "scenarios": ElementProperty(PropertyType.lov, f"{{{__CTX_VAR_NAME}.get_scenarios()}}"),
                "on_scenario_crud": ElementProperty(PropertyType.function, f"{{{__CTX_VAR_NAME}.crud_scenario}}"),
                "configs": ElementProperty(PropertyType.react, f"{{{__CTX_VAR_NAME}.get_scenario_configs()}}"),
                "core_changed": ElementProperty(PropertyType.broadcast, GuiCoreContext._CORE_CHANGED_NAME),
                "error": ElementProperty(PropertyType.react, f"{{{GuiCoreContext._SCENARIO_SELECTOR_ERROR_VAR}}}"),
                "type": ElementProperty(PropertyType.inner, Scenario),
                "adapter": ElementProperty(PropertyType.inner, GuiCoreContext.scenario_adapter),
                "scenario_edit": ElementProperty(
                    GuiCoreScenarioAdapter,
                    f"{{{__CTX_VAR_NAME}.get_scenario_by_id({GuiCoreContext._SCENARIO_SELECTOR_ID_VAR})}}",
                ),
                "on_scenario_select": ElementProperty(PropertyType.function, f"{{{__CTX_VAR_NAME}.select_scenario}}"),
            },
        ),
        "scenario_visualizer": Element(
            "scenario",
            {
                "scenario": ElementProperty(GuiCoreScenarioAdapter),
            },
            inner_properties={
                "on_scenario_edit": ElementProperty(PropertyType.function, f"{{{__CTX_VAR_NAME}.edit_scenario}}"),
                "core_changed": ElementProperty(PropertyType.broadcast, GuiCoreContext._CORE_CHANGED_NAME),
                "error": ElementProperty(PropertyType.react, f"{{{GuiCoreContext._SCENARIO_VIZ_ERROR_VAR}}}"),
            },
        ),
    }

    def get_name(self) -> str:
        return GuiCore.__LIB_NAME

    def get_elements(self) -> t.Dict[str, Element]:
        return GuiCore.__elts

    def get_scripts(self) -> t.List[str]:
        return ["lib/taipy-gui-core.js"]

    def on_init(self, gui: Gui) -> t.Optional[t.Tuple[str, t.Any]]:
        return GuiCore.__CTX_VAR_NAME, GuiCoreContext(gui)

    def on_user_init(self, state: State):
        for var in [
            GuiCoreContext._SCENARIO_SELECTOR_ERROR_VAR,
            GuiCoreContext._SCENARIO_SELECTOR_ID_VAR,
            GuiCoreContext._SCENARIO_VIZ_ERROR_VAR,
        ]:
            state._add_attribute(var)
            state._gui._bind_var_val(var, "")

    def get_version(self) -> str:
        if not hasattr(self, "version"):
            self.version = _get_version()
        return self.version
