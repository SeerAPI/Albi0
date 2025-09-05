from typing import Protocol, TypeVar


class ProcessorProtocol(Protocol):
    name: str
    desc: str


T_Processor = TypeVar("T_Processor", bound=ProcessorProtocol)


class ProcessorContainer(dict[str, T_Processor]):
    def get_by_group(self, group_name: str) -> set[T_Processor]:
        """根据组名获取整组Processor"""
        processors = {v for k, v in self.items() if k.split(".")[0] == group_name}
        return processors

    def get_processors(self, name: str) -> set[T_Processor]:
        """如果传入的参数为组名则获取整组Processor，否则获取单个"""
        return {processor} if (processor := self.get(name)) else self.get_by_group(name)
