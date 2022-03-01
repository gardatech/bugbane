# Фаззинг-тестирование модуля {{ data.module_name }}
Фаззинг-тестирование модуля {{ data.module_name }}, написанного на {% if data.language|length > 1 %}языках{% else %}языке{% endif %} программирования {{ data.language|join(', ') }}, было выполнено с использованием фаззера с обратной связью по покрытию {{ data.fuzzer_type }}{% if data.fuzzer_version %}{{ data.fuzzer_version }}{% endif %} в среде {{ data.os_name }} {{ data.os_version }} в режиме статической инструментации кода. {% if data.sanitizers %}{% if data.sanitizers|length > 1 %}Использованы санитайзеры{% else %}Использован санитайзер{% endif %} {{ data.sanitizers|join(', ') }}. {% endif %}Для сбора информации о покрытии исходного кода использованы инструменты {{ data.coverage_tools|join(', ') }}. Использована коллекция семплов, составленная на основе данных из юнит-тестов, а также данных, поступающих в модуль при нормальной работе. Использован словарь, составленный на основе изучения исходного кода тестируемого приложения.<br>
Тестирование модуля выполняется Разработчиком на регулярной основе. Результаты проведения фаззинг-тестирования помещены в электронные приложения (каталог «Электронные приложения/ДАО.2/{{ data.module_name }}») и проанализированы на предмет выявления кодовых и архитектурных уязвимостей.<br>
Модуль реализован {% if data.is_library %}библиотекой{% else %}приложением{% endif %} {% if data.is_open_source %}с открытым исходным кодом{% else %}собственной разработки{% endif %} {{ data.application_name }} и используется в продукте {{ data.product_name }}{%if data.product_version %} версии {{ data.product_version }}{% endif %} для разбора данных в {% if not data.parse_format or data.parse_format|length < 2 %}сложном структурированном формате{% if data.parse_format %} {{ data.parse_format|join(', ') }}{% endif %}{% else %}сложных структурированных форматах {{ data.parse_format|join(', ') }}{% endif %}.<br>

# Сборка приложения
При сборке приложения компиляторами фаззера {{ data.fuzzer_type }} тестируемая функция {{ data.tested_source_function }} в файле {{ data.tested_source_file }} помещается в цикл, обеспечивая persistent-режим работы фаззера. Данные от фаззера поступают в эту функцию из {% if data.run_args and '@@' in data.run_args %}входного файла{% else %}стандартного ввода{% endif %}.
<br>
{% if data.build_cmds %}Сборка выполняется следующими командами:
```
{{ data.build_cmds }}
```
<br>{% endif %}
{% if data.fuzz_cmds %}
Команды запуска фаззера:
```
{{ data.fuzz_cmds }}
```
<br>{% endif %}{% if data.stop_conditions.minutes_without_paths %}{# фаззинг для сертификации #}Условием завершения тестирования является отсутствие обнаружения фаззером новых путей выполнения кода в течение {{ data.stop_conditions.minutes_without_paths }} минут.<br>{% elif data.stop_conditions.minutes_run_time %}{# CI-фаззинг #}Условием завершения тестирования является достижение продолжительности тестирования {{ data.stop_conditions.minutes_run_time }} мин.<br>{% endif %}

{% if data.screen_fuzzers or data.screen_stats %}
# Скриншоты работы фаззера
{%- for fuzzer_screen in data.screen_fuzzers %}
{%- if loop.index >= 3 and not loop.last %}{% continue %}{% endif %}
![Окно экземпляра №{{ loop.index }} фаззера перед завершением тестирования]({{ fuzzer_screen }})<br>
{%- endfor %}
{%- endif %}
{%- if data.screen_stats %}
![Статистика работы фаззеров перед завершением тестирования]({{ data.screen_stats }})<br>
{% endif %}

# Результаты
В процессе фаззинг-тестирования на {{ data.fuzz_cores_with_units }} процессора было достигнуто условие остановки:{% if data.stop_conditions.minutes_without_paths %}{# фаззинг для сертификации #} новые пути выполнения кода не обнаруживались в течение {{ data.stop_conditions.minutes_without_paths }} минут. При этом{% endif %} продолжительность фаззинг-тестирования составила {{ data.fuzz_time_real_with_units }}.<br>
{% if data.execs_total %}Всего запусков приложения: {{ data.execs_total }}.<br>{% endif %}
{% if data.num_crashes and data.num_crashes != '0' %}В результате работы фаззера было обнаружено {{ data.num_crashes_with_units }}.<br>{# желательно вставить скриншот #}{% else %}В результате работы фаззера падений обнаружено не было.<br>{% endif %}
{% if data.num_hangs and data.num_hangs != '0' %}Было обнаружено {{ data.num_hangs_with_units }}.<br>{% else %}Зависаний обнаружено не было.<br>{% endif %}{# Если обнаруженные фаззером падения/зависания не воспроизводятся вручную, следует так и написать. В этом случае также желательно приложить скриншот, подтверждающий отсутствие падений/зависаний при запуске приложения с соответствующими тестовыми примерами #}
{% if data.num_crashes and data.num_crashes != '0' or data.num_hangs and data.num_hangs != '0' %}Описанные недостатки были устранены Разработчиком на этапе проведения испытаний.<br>{#<скриншот 4>
Рисунок 4. Система контроля версий. Изменения, внесённые Разработчиком для устранения обнаруженных недостатков
<br>#}{% endif %}
После завершения тестирования было собрано покрытие исходного кода, полученное при запуске тестируемого приложения с каждым из обнаруженных фаззером тестовых примеров.<br>
Покрытие исходного кода составило {% if data.cov_func %}по функциям - {{ data.cov_func }}%, {% endif %}по строкам – {{ data.cov_line }}%{% if data.cov_bb %}, по базовым блокам – {{ data.cov_bb }}%{% endif %}.<br>
{%- if data.screen_coverage %}
![Отчёт о покрытии исходного кода тестируемого приложения]({{ data.screen_coverage }})<br>
{%- endif %}
