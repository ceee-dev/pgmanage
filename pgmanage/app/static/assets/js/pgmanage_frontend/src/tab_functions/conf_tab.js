import { beforeCloseTab } from "../create_tab_functions";
import { removeTab, showMenuNewTab } from "../workspace";
import ConfigTab from "../components/ConfigTab.vue";
import { createApp } from "vue";
export let createConfTab = function () {
  // Removing last tab of the inner tab list
  v_connTabControl.selectedTab.tag.tabControl.removeLastTab();

  let tab = v_connTabControl.selectedTab.tag.tabControl.createTab({
    p_name: "<span>Configuration</span>",
    p_closeFunction: function (e, tab) {
      let current_tab = tab;
      beforeCloseTab(e, function () {
        current_tab.app.unmount();
        removeTab(current_tab);
      });
    },
  });

  // Selecting the newly created tab
  v_connTabControl.selectedTab.tag.tabControl.selectTab(tab);

  tab.elementDiv.innerHTML = `
  <div id='configuration_tab_${tab.id}' class="p-2">
    <config-tab></config-tab>
  </div>`;

  let tag = {
    tab_id: tab.id,
    mode: "configuration",
    div_result: document.getElementById(`configuration_tab_${tab.id}`),
  };
  tab.tag = tag;

  let app = createApp({
    components: {
      "config-tab": ConfigTab,
    },
  });

  // save app referece in the tab, it will be later used to restroy app instance on tab close
  tab.app = app;
  app.mount(`#configuration_tab_${tab.id}`);

  let add_tab = v_connTabControl.selectedTab.tag.tabControl.createTab({
    p_name: "+",
    p_close: false,
    p_isDraggable: false,
    p_selectable: false,
    p_clickFunction: function (e) {
      showMenuNewTab(e);
    },
  });
  add_tab.tag = {
    mode: "add",
  };
};
