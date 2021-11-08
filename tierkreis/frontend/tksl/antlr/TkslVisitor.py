# Generated from Tksl.g4 by ANTLR 4.9
from antlr4 import *

if __name__ is not None and "." in __name__:
    from .TkslParser import TkslParser
else:
    from TkslParser import TkslParser

# This class defines a complete generic visitor for a parse tree produced by TkslParser.


class TkslVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by TkslParser#start.
    def visitStart(self, ctx: TkslParser.StartContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#FuncDef.
    def visitFuncDef(self, ctx: TkslParser.FuncDefContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#UseDef.
    def visitUseDef(self, ctx: TkslParser.UseDefContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#TypeAlias.
    def visitTypeAlias(self, ctx: TkslParser.TypeAliasContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#use_ids.
    def visitUse_ids(self, ctx: TkslParser.Use_idsContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#code_block.
    def visitCode_block(self, ctx: TkslParser.Code_blockContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#type_.
    def visitType_(self, ctx: TkslParser.Type_Context):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#graph_type.
    def visitGraph_type(self, ctx: TkslParser.Graph_typeContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#f_param_list.
    def visitF_param_list(self, ctx: TkslParser.F_param_listContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#f_param.
    def visitF_param(self, ctx: TkslParser.F_paramContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#CallMap.
    def visitCallMap(self, ctx: TkslParser.CallMapContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#OutputCall.
    def visitOutputCall(self, ctx: TkslParser.OutputCallContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#ConstDecl.
    def visitConstDecl(self, ctx: TkslParser.ConstDeclContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#IfBlock.
    def visitIfBlock(self, ctx: TkslParser.IfBlockContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#Loop.
    def visitLoop(self, ctx: TkslParser.LoopContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#Edge.
    def visitEdge(self, ctx: TkslParser.EdgeContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#FuncCall.
    def visitFuncCall(self, ctx: TkslParser.FuncCallContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#Thunk.
    def visitThunk(self, ctx: TkslParser.ThunkContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#arglist.
    def visitArglist(self, ctx: TkslParser.ArglistContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#named_map.
    def visitNamed_map(self, ctx: TkslParser.Named_mapContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#positional_args.
    def visitPositional_args(self, ctx: TkslParser.Positional_argsContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#port_map.
    def visitPort_map(self, ctx: TkslParser.Port_mapContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#outport.
    def visitOutport(self, ctx: TkslParser.OutportContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#thunkable_port.
    def visitThunkable_port(self, ctx: TkslParser.Thunkable_portContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#const_assign.
    def visitConst_assign(self, ctx: TkslParser.Const_assignContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#struct_const.
    def visitStruct_const(self, ctx: TkslParser.Struct_constContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#macro_const.
    def visitMacro_const(self, ctx: TkslParser.Macro_constContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#vec_const.
    def visitVec_const(self, ctx: TkslParser.Vec_constContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#const_.
    def visitConst_(self, ctx: TkslParser.Const_Context):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#f_name.
    def visitF_name(self, ctx: TkslParser.F_nameContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#AnonStruct.
    def visitAnonStruct(self, ctx: TkslParser.AnonStructContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#NamedStruct.
    def visitNamedStruct(self, ctx: TkslParser.NamedStructContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#port_label.
    def visitPort_label(self, ctx: TkslParser.Port_labelContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#bool_token.
    def visitBool_token(self, ctx: TkslParser.Bool_tokenContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by TkslParser#inport.
    def visitInport(self, ctx: TkslParser.InportContext):
        return self.visitChildren(ctx)


del TkslParser
